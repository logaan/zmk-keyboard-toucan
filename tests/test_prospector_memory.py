"""Guard the Prospector battery animation's heap and RAM headroom."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-builds.py"
spec = importlib.util.spec_from_file_location("check_builds", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def memory_config(heap=32768, buffer=50, stack=4096):
    return {f"CONFIG_LV_Z_MEM_POOL_SIZE={heap}",
            f"CONFIG_LV_Z_VDB_SIZE={buffer}",
            f"CONFIG_ZMK_DISPLAY_DEDICATED_THREAD_STACK_SIZE={stack}"}


class ProspectorMemoryTests(unittest.TestCase):
    def test_animation_memory_budget(self):
        checker.check_prospector_memory(memory_config())

    def test_original_heap_that_failed_on_hardware(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_memory(memory_config(heap=10000))

    def test_full_screen_draw_buffer_leaves_too_little_headroom(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_memory(memory_config(buffer=100))

    def test_invalid_draw_buffer(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_memory(memory_config(buffer=0))

    def test_display_stack_below_module_recommendation(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_memory(memory_config(stack=2048))

    def test_full_refresh_cannot_use_partial_buffer(self):
        with self.assertRaises(AssertionError):
            checker.check_prospector_memory(memory_config() | {"CONFIG_LV_Z_FULL_REFRESH=y"})

    def test_more_heap_and_smaller_buffer_are_allowed(self):
        checker.check_prospector_memory(memory_config(heap=49152, buffer=25, stack=8192))

    def test_missing_memory_settings(self):
        for setting in memory_config():
            with self.subTest(setting=setting), self.assertRaises(AssertionError):
                checker.check_prospector_memory(memory_config() - {setting})


if __name__ == "__main__":
    unittest.main()
