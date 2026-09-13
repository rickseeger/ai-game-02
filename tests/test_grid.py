import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk.world.grid import TYPE_TABLE, Grid


class TestGrid(unittest.TestCase):
    def test_set_get_roundtrip(self):
        g = Grid(10, 10)
        g.set(3, 4, 1, height=5, floor_z=0, seed=99)
        self.assertEqual(g.get(3, 4), (1, 5, 0, 99))

    def test_out_of_bounds(self):
        g = Grid(10, 10)
        self.assertIsNone(g.get(-1, 0))
        self.assertIsNone(g.get(0, 10))
        self.assertFalse(g.is_solid(-1, 0))
        self.assertFalse(g.is_solid(11, 5))

    def test_solidity(self):
        g = Grid(10, 10)
        g.set(2, 2, 1, height=1)
        self.assertTrue(g.is_solid(2, 2))
        self.assertFalse(g.is_solid(3, 3))
        g.set(4, 4, 4)  # asphalt floor, non-solid
        self.assertFalse(g.is_solid(4, 4))

    def test_type_table(self):
        self.assertTrue(TYPE_TABLE[1]["solid"])
        self.assertTrue(TYPE_TABLE[3]["solid"])
        self.assertFalse(TYPE_TABLE[0]["solid"])
        self.assertFalse(TYPE_TABLE[9]["solid"])


if __name__ == "__main__":
    unittest.main()
