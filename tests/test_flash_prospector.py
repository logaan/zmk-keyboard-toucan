"""Exercise the Operator wizard without GitHub, USB devices, or destructive writes."""

from contextlib import redirect_stdout
import errno
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/flash-prospector"
loader = importlib.machinery.SourceFileLoader("flash_prospector", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
flasher = importlib.util.module_from_spec(spec)
loader.exec_module(flasher)


def uf2(family=0xADA52840, address=0x27000, block=0, total=1):
    data = bytearray(512)
    struct.pack_into("<8I", data, 0, 0x0A324655, 0x9E5D5157, 0x2000,
                     address, 256, block, total, family)
    struct.pack_into("<I", data, 508, 0x0AB16F30)
    return bytes(data)


class FlashProspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        images = {}
        for device, name in flasher.FILENAMES.items():
            (self.bundle / name).write_bytes(uf2())
            images[device] = {"file": name, "sha256": flasher.sha256(uf2())}
        self.manifest = {"format": 1, "profile": "prospector", "display": "operator",
                         "source_sha256": flasher.source_fingerprint(), "images": images}
        self.save_manifest()
        self.volumes = self.root / "Volumes"
        self.volumes.mkdir()

    def save_manifest(self):
        (self.bundle / "bundle.json").write_text(json.dumps(self.manifest))

    def board(self, name="XIAO-SENSE", board_id="Seeed_XIAO_nRF52840_Sense"):
        volume = self.volumes / name
        volume.mkdir()
        (volume / "INFO_UF2.TXT").write_text(f"UF2 Bootloader\nBoard-ID: {board_id}\n")
        return volume

    def test_matching_bundle_is_accepted(self):
        self.assertEqual(flasher.load_bundle(self.bundle)["display"], "operator")

    def test_corrupt_image_is_rejected_before_any_device_access(self):
        (self.bundle / flasher.FILENAMES["right"]).write_bytes(b"corrupt")
        with mock.patch.object(flasher, "find_bootloader") as find:
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                flasher.load_bundle(self.bundle)
            find.assert_not_called()

    def test_missing_image_is_rejected(self):
        (self.bundle / flasher.FILENAMES["left"]).unlink()
        with self.assertRaises(FileNotFoundError):
            flasher.load_bundle(self.bundle)

    def test_stale_bundle_is_rejected(self):
        self.manifest["source_sha256"] = "old sources"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "sources changed"):
            flasher.load_bundle(self.bundle)

    def test_other_display_or_profile_is_rejected(self):
        for key, value in (("display", "classic"), ("profile", "standalone")):
            with self.subTest(key=key):
                original = self.manifest[key]
                self.manifest[key] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "Operator firmware bundle"):
                    flasher.load_bundle(self.bundle)
                self.manifest[key] = original

    def test_wrong_role_filename_is_rejected(self):
        self.manifest["images"]["left"]["file"] = "toucan_left-zmk.uf2"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Wrong image selected for left"):
            flasher.load_bundle(self.bundle)

    def test_paths_outside_bundle_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe image path"):
            flasher.checked_image(self.bundle, {"file": "../outside.uf2"})

    def test_valid_uf2_is_accepted(self):
        flasher.validate_uf2(uf2())

    def test_bad_uf2_is_rejected(self):
        for data in (b"", uf2()[:-1], b"\0" * 512, uf2(family=0x1234),
                     uf2(address=0), uf2(address=0xF8000), uf2(total=2),
                     uf2(total=2) + uf2(total=2)):
            with self.subTest(data_length=len(data)), self.assertRaises(ValueError):
                flasher.validate_uf2(data)

    def test_dry_run_does_not_need_a_terminal_or_devices(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--dry-run",
                                 "--firmware-dir", str(self.bundle)],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry run: no devices accessed or flashed.", result.stdout)
        for name in flasher.FILENAMES.values():
            self.assertIn(name, result.stdout)

    def test_no_bootloader_returns_none(self):
        self.assertIsNone(flasher.find_bootloader(self.volumes))

    def test_auto_disconnected_bootloader_does_not_break_scanning(self):
        self.board()
        with mock.patch.object(Path, "stat", side_effect=OSError(errno.EIO, "device disappeared")):
            self.assertIsNone(flasher.find_bootloader(self.volumes))

    def test_xiao_bootloader_is_accepted(self):
        volume = self.board()
        self.assertEqual(flasher.find_bootloader(self.volumes),
                         (volume, "Seeed_XIAO_nRF52840_Sense"))

    def test_multiple_bootloaders_are_rejected(self):
        self.board()
        self.board("SECOND-XIAO")
        with self.assertRaisesRegex(ValueError, "More than one UF2 drive"):
            flasher.find_bootloader(self.volumes)

    def test_unknown_board_is_rejected(self):
        self.board(board_id="Raspberry-Pi-Pico")
        with self.assertRaisesRegex(ValueError, "non-XIAO"):
            flasher.find_bootloader(self.volumes)

    def test_mac_copy_excludes_metadata(self):
        with mock.patch.object(flasher.platform, "system", return_value="Darwin"), \
             mock.patch.object(flasher.subprocess, "run",
                               return_value=subprocess.CompletedProcess(["cp"], 0)) as run:
            flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], self.volumes)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["cp", "-X", str(self.bundle / flasher.FILENAMES["dongle"]),
                          str(self.volumes / "firmware.uf2")])
        self.assertTrue(run.call_args.kwargs["capture_output"])
        run.assert_called_once()  # No global sync after the device has disconnected.

    def test_copy_error_after_auto_disconnect_is_expected(self):
        volume = self.board()
        error = subprocess.CalledProcessError(
            1, ["cp", "-X"], stderr="fcopyfile failed: Input/output error\nfchmod failed: No such file or directory")

        def disconnect(*args, **kwargs):
            (volume / "INFO_UF2.TXT").unlink()
            volume.rmdir()
            raise error

        output = io.StringIO()
        with mock.patch.object(flasher.subprocess, "run", side_effect=disconnect), \
             mock.patch.object(flasher.time, "sleep") as sleep, redirect_stdout(output):
            flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)
        self.assertIn("auto-disconnected", output.getvalue())
        self.assertIn("expected copy/sync error", output.getvalue())
        sleep.assert_not_called()

    def test_copy_error_allows_time_for_the_volume_to_disappear(self):
        error = subprocess.CalledProcessError(1, ["cp"], stderr="Input/output error")
        with mock.patch.object(flasher.subprocess, "run", side_effect=error), \
             mock.patch.object(flasher, "bootloader_present", side_effect=[True, False]), \
             mock.patch.object(flasher.time, "sleep") as sleep, redirect_stdout(io.StringIO()):
            flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], self.volumes)
        sleep.assert_called_once_with(0.3)

    def test_copy_error_with_bootloader_still_mounted_is_fatal(self):
        volume = self.board()
        error = subprocess.CalledProcessError(1, ["cp"], stderr="No space left on device")
        with mock.patch.object(flasher.subprocess, "run", side_effect=error), \
             mock.patch.object(flasher.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(OSError, "still mounted:\nNo space left on device"):
                flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)

    def test_transfer_timeout_after_auto_disconnect_is_expected(self):
        error = subprocess.TimeoutExpired(["cp"], 60, stderr=b"Input/output error")
        with mock.patch.object(flasher.subprocess, "run", side_effect=error), \
             mock.patch.object(flasher, "bootloader_present", return_value=False), \
             redirect_stdout(io.StringIO()):
            flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], self.volumes)

    def test_transfer_timeout_with_bootloader_still_mounted_is_fatal(self):
        volume = self.board()
        error = subprocess.TimeoutExpired(["cp"], 60, stderr=b"Input/output error")
        with mock.patch.object(flasher.subprocess, "run", side_effect=error), \
             mock.patch.object(flasher.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(OSError, "still mounted:\nInput/output error"):
                flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)

    def test_sync_error_after_auto_disconnect_is_expected(self):
        volume = self.board()

        def run(command, **kwargs):
            if command == ["sync"]:
                (volume / "INFO_UF2.TXT").unlink()
                raise subprocess.CalledProcessError(1, command, stderr="Device not configured")
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(flasher.subprocess, "run", side_effect=run) as execute, \
             redirect_stdout(io.StringIO()):
            flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(execute.call_args.args[0], ["sync"])

    def test_sync_error_with_bootloader_still_mounted_is_fatal(self):
        volume = self.board()
        results = [subprocess.CompletedProcess(["cp"], 0),
                   subprocess.CalledProcessError(1, ["sync"], stderr="Input/output error")]
        with mock.patch.object(flasher.subprocess, "run", side_effect=results), \
             mock.patch.object(flasher.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(OSError, "still mounted:\nInput/output error"):
                flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)

    def test_successful_copy_without_a_disconnect_times_out(self):
        volume = self.board()
        with mock.patch.object(flasher.subprocess, "run",
                               return_value=subprocess.CompletedProcess(["cp"], 0)), \
             mock.patch.object(flasher.time, "monotonic", side_effect=[0, 31]):
            with self.assertRaisesRegex(TimeoutError, "did not disconnect"):
                flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], volume)

    def test_missing_copy_command_is_not_mistaken_for_a_disconnect(self):
        with mock.patch.object(flasher.subprocess, "run", side_effect=FileNotFoundError("cp")):
            with self.assertRaises(FileNotFoundError):
                flasher.copy_uf2(self.bundle / flasher.FILENAMES["dongle"], self.volumes)

    def test_disconnected_bootloader_probe_errors_are_expected(self):
        for code in (errno.ENOENT, errno.ENODEV, errno.ENXIO, errno.EIO):
            with self.subTest(errno=code), \
                 mock.patch.object(Path, "stat", side_effect=OSError(code, "device disappeared")):
                self.assertFalse(flasher.bootloader_present(self.volumes))

    def test_unrelated_bootloader_probe_errors_are_not_ignored(self):
        with mock.patch.object(Path, "stat", side_effect=PermissionError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                flasher.bootloader_present(self.volumes)

    def test_reset_and_firmware_can_be_skipped_before_device_access(self):
        for reset in (True, False):
            for answer in ("s", "skip", "S", "SKIP"):
                with self.subTest(reset=reset, answer=answer), \
                     mock.patch("builtins.input", return_value=answer), \
                     mock.patch.object(flasher, "wait_for_bootloader") as wait, \
                     mock.patch.object(flasher, "find_bootloader") as find, \
                     mock.patch.object(flasher, "checked_image") as check, \
                     mock.patch.object(flasher, "copy_uf2") as copy, \
                     mock.patch.object(flasher.time, "sleep") as sleep, redirect_stdout(io.StringIO()):
                    self.assertFalse(flasher.flash(self.bundle, self.manifest, "dongle", reset=reset))
                    wait.assert_not_called()
                    find.assert_not_called()
                    check.assert_not_called()
                    copy.assert_not_called()
                    sleep.assert_not_called()

    def test_reset_and_firmware_can_be_skipped_at_device_confirmation(self):
        volume = self.board()
        for reset in (True, False):
            with self.subTest(reset=reset), mock.patch("builtins.input", side_effect=["", "s"]), \
                 mock.patch.object(flasher, "wait_for_bootloader", return_value=(volume, "board")), \
                 mock.patch.object(flasher, "copy_uf2") as copy, redirect_stdout(io.StringIO()):
                self.assertFalse(flasher.flash(self.bundle, self.manifest, "dongle", reset=reset))
                copy.assert_not_called()

    def test_invalid_step_answer_does_not_start_waiting_or_writing(self):
        with mock.patch("builtins.input", side_effect=["not enter", "s"]), \
             mock.patch.object(flasher, "wait_for_bootloader") as wait, \
             mock.patch.object(flasher, "copy_uf2") as copy, redirect_stdout(io.StringIO()):
            self.assertFalse(flasher.flash(self.bundle, self.manifest, "dongle"))
            wait.assert_not_called()
            copy.assert_not_called()

    def test_skip_does_not_bypass_erase_confirmation(self):
        with mock.patch("builtins.input", side_effect=["s", "ERASE"]) as answer, \
             redirect_stdout(io.StringIO()):
            self.assertTrue(flasher.confirm("Enable resets: ", "ERASE"))
        self.assertEqual(answer.call_count, 2)

    def test_changed_bootloader_is_not_flashed(self):
        volume = self.board()
        with mock.patch.object(flasher, "ask", side_effect=["", "dongle"]), \
             mock.patch.object(flasher, "wait_for_bootloader", return_value=(volume, "board")), \
             mock.patch.object(flasher, "find_bootloader", return_value=None), \
             mock.patch.object(flasher, "copy_uf2") as copy:
            with self.assertRaisesRegex(ValueError, "Bootloader changed"):
                flasher.flash(self.bundle, self.manifest, "dongle")
            copy.assert_not_called()

    def test_quit_before_write_does_not_flash(self):
        volume = self.board()
        with mock.patch("builtins.input", side_effect=["", "q"]), \
             mock.patch.object(flasher, "wait_for_bootloader", return_value=(volume, "board")), \
             mock.patch.object(flasher, "copy_uf2") as copy:
            with self.assertRaises(KeyboardInterrupt):
                flasher.flash(self.bundle, self.manifest, "dongle")
            copy.assert_not_called()

    def test_clean_setup_resets_then_flashes_each_device(self):
        with mock.patch.object(flasher, "ask", side_effect=["1", "ERASE", "", "", "", ""]), \
             mock.patch.object(flasher, "find_bootloader", return_value=None), \
             mock.patch.object(flasher, "flash") as flash:
            flasher.wizard(self.bundle, self.manifest)
        self.assertEqual([(call.args[2], call.kwargs.get("reset", False))
                          for call in flash.call_args_list],
                         [("dongle", True), ("dongle", False), ("left", True),
                          ("left", False), ("right", True), ("right", False)])

    def test_wizard_can_skip_any_step_and_resume_after_the_dongle(self):
        volume = self.board()
        found = (volume, "board")
        skip_sets = [{index} for index in range(6)] + [{0, 1}, set(range(6))]
        for skip_steps in skip_sets:
            with self.subTest(skip_steps=skip_steps):
                answers = ["1", "ERASE", ""]
                probes = []
                expected_images = []
                for index, device in enumerate(flasher.LABELS):
                    for offset, reset in enumerate((True, False)):
                        if index * 2 + offset in skip_steps:
                            answers.append("s")
                        else:
                            answers.extend(["", device])
                            probes.append(found)
                            expected_images.append(flasher.FILENAMES["reset" if reset else device])
                    if not {index * 2, index * 2 + 1} <= skip_steps:
                        answers.append("")  # Disconnect after a device with a write.
                    probes.append(None)
                output = io.StringIO()
                with mock.patch("builtins.input", side_effect=answers) as answer, \
                     mock.patch.object(flasher, "wait_for_bootloader", return_value=found) as wait, \
                     mock.patch.object(flasher, "find_bootloader", side_effect=probes) as find, \
                     mock.patch.object(flasher, "copy_uf2") as copy, \
                     mock.patch.object(flasher.time, "sleep"), redirect_stdout(output):
                    flasher.wizard(self.bundle, self.manifest)
                self.assertEqual([call.args[0].name for call in copy.call_args_list], expected_images)
                self.assertEqual(wait.call_count, len(expected_images))
                self.assertEqual(answer.call_count, len(answers))
                self.assertEqual(find.call_count, len(probes))
                self.assertIn(f"{6 - len(skip_steps)} written, {len(skip_steps)} skipped", output.getvalue())
                self.assertIn("Skipped steps were NOT verified", output.getvalue())

    def test_skipping_a_mounted_device_still_requires_disconnection(self):
        volume = self.board()
        with mock.patch.object(flasher, "ask", side_effect=["1", "ERASE", "", ""]), \
             mock.patch.object(flasher, "flash", return_value=False) as flash, \
             mock.patch.object(flasher, "find_bootloader", return_value=(volume, "board")), \
             redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "bootloader is still connected"):
                flasher.wizard(self.bundle, self.manifest)
        self.assertEqual(flash.call_count, 2)  # Does not move on to the next device.

    def test_update_never_resets_settings(self):
        with mock.patch.object(flasher, "ask", side_effect=["2", "", "", "", ""]), \
             mock.patch.object(flasher, "find_bootloader", return_value=None), \
             mock.patch.object(flasher, "flash") as flash:
            flasher.wizard(self.bundle, self.manifest)
        self.assertEqual([call.args[2] for call in flash.call_args_list], ["dongle", "left", "right"])
        self.assertTrue(all(not call.kwargs.get("reset", False) for call in flash.call_args_list))

    def test_refusing_erase_confirmation_never_flashes(self):
        with mock.patch("builtins.input", side_effect=["1", "q"]), \
             mock.patch.object(flasher, "flash") as flash:
            with self.assertRaises(KeyboardInterrupt):
                flasher.wizard(self.bundle, self.manifest)
            flash.assert_not_called()

    def test_preparer_checks_compiled_roles_and_requires_operator(self):
        builds = self.root / "build"
        for device, names in flasher.BUILDS.items():
            zephyr = builds / names[0] / "zephyr"
            generated = zephyr / "include/generated/zephyr"
            generated.mkdir(parents=True)
            (generated / "version.h").write_text('#define KERNEL_VERSION_STRING "4.1.0"\n')
            (generated / "app_version.h").write_text("same ZMK revision\n")
            (zephyr / ".config").write_text("CONFIG_PROSPECTOR_STATUS_SCREEN_OPERATOR=y\n")
            (zephyr / "zmk.uf2").write_bytes(uf2())
        with mock.patch.object(flasher.runpy, "run_path", return_value={"check": mock.Mock()}) as load:
            destination = self.root / "prepared"
            flasher.prepare_bundle(builds, destination)
            self.assertEqual(load.return_value["check"].call_count, 4)
            self.assertEqual(flasher.load_bundle(destination)["display"], "operator")
            (builds / "prospector/zephyr/.config").write_text("CONFIG_PROSPECTOR_STATUS_SCREEN_CLASSIC=y\n")
            with self.assertRaisesRegex(ValueError, "not using the Operator"):
                flasher.prepare_bundle(builds, destination)


if __name__ == "__main__":
    unittest.main()
