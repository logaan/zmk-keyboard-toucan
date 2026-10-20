"""Check the indexed LCD assets after their LVGL 9 descriptor migration."""

from pathlib import Path
import re
import unittest


DISPLAY = Path(__file__).resolve().parents[1] / "boards/shields/nice_view_gem"


class DisplayAssetTests(unittest.TestCase):
    def test_indexed_image_headers_and_storage(self):
        for path, count in ((DISPLAY / "assets/images.c", 15),
                            (DISPLAY / "widgets/sleep.c", 1)):
            source = path.read_text()
            arrays = dict(re.findall(r"uint8_t (\w+)\[\] = \{(.*?)\};", source, re.DOTALL))
            images = re.findall(r"const lv_image_dsc_t (\w+) = \{(.*?)\};", source, re.DOTALL)
            self.assertEqual(len(images), count, str(path))
            for name, descriptor in images:
                with self.subTest(image=name):
                    self.assertIn(".header.magic = LV_IMAGE_HEADER_MAGIC", descriptor)
                    self.assertIn(".header.cf = LV_COLOR_FORMAT_I1", descriptor)
                    width = int(re.search(r"\.header.w = (\d+)", descriptor)[1])
                    height = int(re.search(r"\.header.h = (\d+)", descriptor)[1])
                    stride = int(re.search(r"\.header.stride = (\d+)", descriptor)[1])
                    data = re.search(r"\.data = (\w+)", descriptor)[1]
                    actual_size = len(re.findall(r"0x[0-9a-fA-F]{2}\b", arrays[data]))
                    size_expr = re.search(r"\.data_size = ([^,]+),", descriptor)[1]
                    size = actual_size if size_expr == f"sizeof({data})" else int(size_expr)
                    self.assertEqual(stride, (width + 7) // 8)
                    self.assertEqual(size, stride * height + 8)  # two BGRA palette entries
                    self.assertEqual(size, actual_size)


if __name__ == "__main__":
    unittest.main()
