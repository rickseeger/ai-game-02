import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk.assets.glyphsets import RAMP, ramp_glyph
from citywalk.assets.palettes import PALETTES
from citywalk.renderer.palette import fog, lerp, rgb_to_256


class TestPalette(unittest.TestCase):
    def test_palettes_are_valid_rgb_triples(self):
        for name, rgb in PALETTES.items():
            self.assertEqual(len(rgb), 3, name)
            for c in rgb:
                self.assertIsInstance(c, int, name)
                self.assertTrue(0 <= c <= 255, name)

    def test_ramp_is_ascii_and_long(self):
        self.assertGreater(len(RAMP), 60)
        for ch in RAMP:
            self.assertTrue(32 <= ord(ch) <= 126, repr(ch))

    def test_ramp_mapping_endpoints(self):
        self.assertEqual(ramp_glyph(0.0), RAMP[0])
        self.assertEqual(ramp_glyph(1.0), RAMP[-1])
        self.assertEqual(ramp_glyph(-5.0), RAMP[0])
        self.assertEqual(ramp_glyph(5.0), RAMP[-1])
        mid = ramp_glyph(0.5)
        self.assertIn(mid, RAMP)

    def test_rgb_to_256_range_and_endpoints(self):
        for r in (0, 40, 128, 200, 255):
            i = rgb_to_256((r, 0, 0))
            self.assertTrue(0 <= i <= 255)
        self.assertEqual(rgb_to_256((0, 0, 0)), 16)
        self.assertEqual(rgb_to_256((255, 255, 255)), 231)

    def test_lerp_and_fog(self):
        self.assertEqual(lerp((0, 0, 0), (100, 100, 100), 0.5), (50, 50, 50))
        self.assertEqual(lerp((0, 0, 0), (100, 100, 100), 1.0), (100, 100, 100))
        self.assertEqual(fog((255, 255, 255), 0.0), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
