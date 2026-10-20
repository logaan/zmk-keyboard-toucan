"""Exercise artifact/profile selection without GitHub access or USB devices."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build-and-load"
LEFT = "toucan_left rgbled_adapter nice_view_gem-seeeduino_xiao_ble-zmk.uf2"
RIGHT = "toucan_right rgbled_adapter-seeeduino_xiao_ble-zmk.uf2"
PERIPHERAL = "toucan_left_peripheral-zmk.uf2"
DONGLE = "toucan_prospector-zmk.uf2"
RESET = "settings_reset-seeeduino_xiao_ble-zmk.uf2"


class BuildAndLoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.fixtures = root / "fixtures"
        self.artifacts = self.fixtures / "firmware"
        self.artifacts.mkdir(parents=True)
        for name in (LEFT, RIGHT, PERIPHERAL, DONGLE, RESET):
            (self.artifacts / name).write_bytes(b"test UF2")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys
args = sys.argv[1:]
if args[:2] == ["auth", "status"]:
    sys.exit(1 if os.environ.get("GH_AUTH_FAIL") else 0)
if args[:2] == ["run", "list"]:
    print("42")
elif args[:2] == ["run", "view"]:
    field = args[args.index("--json") + 1]
    print("completed" if field == "status" else os.environ.get("GH_CONCLUSION", "success"))
elif args[:2] == ["run", "download"]:
    shutil.copytree(os.environ["FW_FIXTURES"], args[args.index("-D") + 1], dirs_exist_ok=True)
else:
    sys.exit("unexpected gh invocation: " + repr(args))
''')
        gh.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                        FW_FIXTURES=str(self.fixtures), TERM="dumb")

    def run_script(self, *args, dry_run=True):
        command = [str(SCRIPT), "--run", "42"]
        if dry_run:
            command.append("--dry-run")
        return subprocess.run(command + list(args), env=self.env, text=True,
                              capture_output=True, timeout=10)

    def selected(self, *args):
        result = self.run_script(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry run: no devices flashed.", result.stdout)
        self.assertNotIn("Waiting for the bootloader", result.stdout)
        return [line.split(": ", 1)[1] for line in result.stdout.splitlines()
                if line.startswith("  ") and line.endswith(".uf2")]

    def test_default_is_standalone_even_with_both_images_available(self):
        self.assertEqual(self.selected(), [LEFT, RIGHT])

    def test_explicit_standalone(self):
        self.assertEqual(self.selected("--profile", "standalone"), [LEFT, RIGHT])

    def test_prospector_default_flashes_three_matching_images(self):
        self.assertEqual(self.selected("--profile", "prospector"),
                         [DONGLE, PERIPHERAL, RIGHT])

    def test_prospector_left_does_not_select_standalone(self):
        self.assertEqual(self.selected("--profile", "prospector", "left"), [PERIPHERAL])

    def test_right_is_shared(self):
        self.assertEqual(self.selected("right"), [RIGHT])
        self.assertEqual(self.selected("--profile", "prospector", "right"), [RIGHT])

    def test_both_still_means_halves_only(self):
        self.assertEqual(self.selected("--profile", "prospector", "both"), [PERIPHERAL, RIGHT])

    def test_reset_is_explicit_and_does_not_select_normal_firmware(self):
        self.assertEqual(self.selected("reset"), [RESET])
        self.assertEqual(self.selected("--profile", "prospector", "reset"), [RESET])

    def test_dongle_is_explicit(self):
        self.assertEqual(self.selected("--profile", "prospector", "dongle"), [DONGLE])
        result = self.run_script("dongle")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dongle requires --profile prospector", result.stderr)

    def test_help_and_argument_errors_work_without_authentication(self):
        self.env["GH_AUTH_FAIL"] = "1"
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--profile prospector", result.stdout)
        for args in (("--profile", "typo"), ("--profile",), ("--run",)):
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("authenticated", result.stdout)

    def test_old_artifacts_still_work_for_standalone(self):
        (self.artifacts / DONGLE).unlink()
        (self.artifacts / PERIPHERAL).unlink()
        self.assertEqual(self.selected(), [LEFT, RIGHT])

    def test_missing_peripheral_must_not_fall_back_to_standalone(self):
        (self.artifacts / PERIPHERAL).unlink()
        result = self.run_script("--profile", "prospector", "left")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one left .uf2 for profile prospector", result.stderr)

    def test_missing_standalone_must_not_fall_back_to_peripheral(self):
        (self.artifacts / LEFT).unlink()
        result = self.run_script("left")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one left .uf2 for profile standalone", result.stderr)

    def test_duplicate_matching_images_are_rejected(self):
        duplicate = self.fixtures / "duplicate"
        duplicate.mkdir()
        (duplicate / LEFT).write_bytes(b"duplicate UF2")
        result = self.run_script("left")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one left", result.stderr)

    def test_every_image_is_resolved_before_any_flashing(self):
        (self.artifacts / RIGHT).unlink()
        result = self.run_script("--profile", "prospector", dry_run=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected exactly one right", result.stderr)
        self.assertNotIn("Waiting for the bootloader", result.stdout)

    def test_failed_ci_is_rejected_before_downloading(self):
        self.env["GH_CONCLUSION"] = "failure"
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CI build did not succeed", result.stderr)
        self.assertNotIn("Downloading", result.stdout)


if __name__ == "__main__":
    unittest.main()
