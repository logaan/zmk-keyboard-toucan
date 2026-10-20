"""Keep the Zephyr 4.1 manifest, reusable workflow, and board matrix aligned."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FirmwareVersionTests(unittest.TestCase):
    def test_ci_workflow_uses_the_pinned_zmk_revision(self):
        manifest = (ROOT / "config/west.yml").read_text()
        project = re.search(r"    - name: zmk\n(.*?)    - name:", manifest, re.DOTALL)[1]
        revision = re.search(r"      revision: ([0-9a-f]{40})\n", project)[1]
        workflow = (ROOT / ".github/workflows/build.yml").read_text()
        self.assertIn(f"zmkfirmware/zmk/.github/workflows/build-user-config.yml@{revision}", workflow)

    def test_prospector_defaults_to_operator(self):
        config = (ROOT / "boards/shields/toucan/toucan_dongle.conf").read_text().splitlines()
        layouts = [line for line in config if line.startswith("CONFIG_PROSPECTOR_STATUS_SCREEN_")]
        self.assertEqual(layouts, ["CONFIG_PROSPECTOR_STATUS_SCREEN_OPERATOR=y"])

    def test_every_target_uses_the_zmk_xiao_variant(self):
        matrix = (ROOT / "build.yaml").read_text()
        boards = re.findall(r"^  - board: (\S+)$", matrix, re.MULTILINE)
        self.assertEqual(boards, ["xiao_ble//zmk"] * 5)
        self.assertNotIn("seeeduino_xiao_ble", matrix)


if __name__ == "__main__":
    unittest.main()
