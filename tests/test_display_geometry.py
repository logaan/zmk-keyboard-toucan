"""Regression coverage for the Toucan LCD vs. stock nice!view panel geometry."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-builds.py"
spec = importlib.util.spec_from_file_location("check_builds", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def display_values(width, height):
    # The same macros consumed from Zephyr's generated devicetree header.
    display = "DT_N_S_soc_S_spi_40003000_S_ls0xx_0"
    return {"DT_CHOSEN_zephyr_display": display,
            display + "_P_width": str(width), display + "_P_height": str(height)}


class DisplayGeometryTests(unittest.TestCase):
    def test_toucan_panel(self):
        checker.check_display_geometry(display_values(144, 168))

    def test_stock_nice_view_is_not_a_toucan_panel(self):
        # The originally compiled peripheral build passed the old checker but
        # produced random streaks on hardware with this 160x68 definition.
        with self.assertRaises(AssertionError):
            checker.check_display_geometry(display_values(160, 68))

    def test_both_toucan_dimensions_must_match(self):
        for dimensions in ((144, 68), (160, 168), (168, 144)):
            with self.subTest(dimensions=dimensions), self.assertRaises(AssertionError):
                checker.check_display_geometry(display_values(*dimensions))

    def test_prospector_panel(self):
        checker.check_display_geometry(display_values(240, 280), dongle=True)

    def test_prospector_and_toucan_are_not_interchangeable(self):
        with self.assertRaises(AssertionError):
            checker.check_display_geometry(display_values(240, 280))
        with self.assertRaises(AssertionError):
            checker.check_display_geometry(display_values(144, 168), dongle=True)


if __name__ == "__main__":
    unittest.main()
