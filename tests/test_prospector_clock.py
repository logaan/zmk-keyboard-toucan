"""Keep the verified split-link clock-accuracy fix in normal firmware."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-builds.py"
spec = importlib.util.spec_from_file_location("check_builds", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ProspectorClockTests(unittest.TestCase):
    def test_verified_accuracy_is_accepted(self):
        checker.check_prospector_clock({"CONFIG_CLOCK_CONTROL_NRF_K32SRC_500PPM=y",
                                        "CONFIG_CLOCK_CONTROL_NRF_ACCURACY=500"})

    def test_original_50ppm_declaration_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "500 ppm"):
            checker.check_prospector_clock({"CONFIG_CLOCK_CONTROL_NRF_K32SRC_50PPM=y",
                                            "CONFIG_CLOCK_CONTROL_NRF_ACCURACY=50"})

    def test_numeric_accuracy_must_match_the_choice(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_clock({"CONFIG_CLOCK_CONTROL_NRF_K32SRC_500PPM=y",
                                            "CONFIG_CLOCK_CONTROL_NRF_ACCURACY=50"})

    def test_accuracy_choice_is_required(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_clock({"CONFIG_CLOCK_CONTROL_NRF_ACCURACY=500"})

    def test_normal_dongle_config_keeps_the_fix(self):
        config = set((SCRIPT.parents[1] / "boards/shields/toucan/toucan_dongle.conf")
                     .read_text().splitlines())
        self.assertIn("CONFIG_CLOCK_CONTROL_NRF_K32SRC_500PPM=y", config)
        self.assertNotIn("CONFIG_CLOCK_CONTROL_NRF_K32SRC_50PPM=y", config)


if __name__ == "__main__":
    unittest.main()
