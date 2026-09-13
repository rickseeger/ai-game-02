"""Procedural city generator tests (DESIGN 5.5): determinism + validity.

Asserts that ``world.gen`` produces a coherent, navigable night city:
  * deterministic (byte-identical for the same seed, different for others);
  * streets form a single connected walkable network from the spawn;
  * buildings are placed on block cells (never on streets) and are solid;
  * restaurants are present (>= N), each with a lit storefront, awning, and
    sidewalk tables/chairs that do not block navigation;
  * terrain varies (sunken harbor water, raised park hills);
  * the border is a closed solid ring so cast rays always terminate.
"""
import os
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk.world import gen
from citywalk.world.grid import (BRICK, CONCRETE, GLASS, ASPHALT, SIDEWALK,
                                 COBBLE, GRASS, WATER, LAMP, TREE, TABLE,
                                 CHAIR, AWNING, FOUNTAIN, SIGN, STOREFRONT)

BUILDING_TYPES = {BRICK, CONCRETE, GLASS, STOREFRONT}


def _reachable(grid, start):
    """Set of walkable (non-solid) cells reachable from ``start`` via 4-dir."""
    sx, sy = int(start[0]), int(start[1])
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if grid.in_bounds(nx, ny) and not grid.is_solid(nx, ny) \
                    and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


class TestCityDeterminism(unittest.TestCase):
    def test_same_seed_is_byte_identical(self):
        a = gen.generate(seed=42)
        b = gen.generate(seed=42)
        self.assertEqual(a.grid.types, b.grid.types)
        self.assertEqual(a.grid.height, b.grid.height)
        self.assertEqual(a.grid.floor_z, b.grid.floor_z)
        self.assertEqual(a.grid.seed, b.grid.seed)
        self.assertEqual(a.spawn, b.spawn)
        self.assertEqual([(r.x, r.y, r.w, r.h) for r in a.restaurants],
                         [(r.x, r.y, r.w, r.h) for r in b.restaurants])
        self.assertEqual(len(a.lights), len(b.lights))

    def test_different_seed_differs(self):
        a = gen.generate(seed=1)
        b = gen.generate(seed=2)
        self.assertNotEqual(a.grid.types, b.grid.types)


class TestCityValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = gen.generate(seed=20260913)
        cls.g = cls.city.grid

    def test_spawn_is_walkable(self):
        x, y = int(self.city.spawn[0]), int(self.city.spawn[1])
        self.assertTrue(self.g.in_bounds(x, y))
        self.assertFalse(self.g.is_solid(x, y))

    def test_streets_fully_connected(self):
        seen = _reachable(self.g, self.city.spawn)
        for y in range(self.g.h):
            for x in range(self.g.w):
                t = self.g.type_of(x, y)
                if t in (ASPHALT, SIDEWALK):
                    self.assertIn((x, y), seen,
                                  "street/sidewalk cell (%d,%d) unreachable" % (x, y))

    def test_buildings_placed_on_blocks(self):
        solid = 0
        for y in range(self.g.h):
            for x in range(self.g.w):
                t = self.g.type_of(x, y)
                if self.g.is_solid(x, y):
                    solid += 1
                    self.assertIn(t, BUILDING_TYPES, (x, y, t))
                    self.assertGreaterEqual(self.g.height[self.g.idx(x, y)], 1)
                if t == ASPHALT:
                    self.assertFalse(self.g.is_solid(x, y))
        self.assertGreater(solid, 1000)

    def test_restaurants_present_with_tables(self):
        self.assertGreaterEqual(len(self.city.restaurants), 6)
        for r in self.city.restaurants:
            self.assertGreaterEqual(len(r.tables), 1, (r.x, r.y))
            self.assertGreaterEqual(len(r.awning), 1, (r.x, r.y))
            # storefront building is solid
            self.assertTrue(self.g.is_solid(r.x, r.y))
            self.assertEqual(self.g.type_of(r.x, r.y), STOREFRONT)
            # tables/chairs/awning are non-solid (do not block navigation)
            for (tx, ty) in r.tables + r.chairs + r.awning:
                self.assertFalse(self.g.is_solid(tx, ty), (tx, ty))
                self.assertIn(self.g.type_of(tx, ty), (TABLE, CHAIR, AWNING),
                              (tx, ty))

    def test_terrain_variation(self):
        water_z = {self.g.floor_z[self.g.idx(x, y)]
                   for y in range(self.g.h) for x in range(self.g.w)
                   if self.g.type_of(x, y) == WATER}
        self.assertTrue(any(z < 0 for z in water_z), water_z)
        park_z = {self.g.floor_z[self.g.idx(x, y)]
                  for y in range(self.g.h) for x in range(self.g.w)
                  if self.g.type_of(x, y) == TREE}
        self.assertTrue(any(z > 0 for z in park_z), park_z)

    def test_border_is_closed_solid_ring(self):
        w, h = self.g.w, self.g.h
        for x in range(w):
            self.assertTrue(self.g.is_solid(x, 0))
            self.assertTrue(self.g.is_solid(x, h - 1))
        for y in range(h):
            self.assertTrue(self.g.is_solid(0, y))
            self.assertTrue(self.g.is_solid(w - 1, y))

    def test_zones_cover_blocks(self):
        zones = {b[4] for b in self.city.blocks}
        self.assertIn(gen.PLAZA, zones)
        self.assertIn(gen.DOWNTOWN, zones)
        self.assertIn(gen.WATERFRONT, zones)


if __name__ == "__main__":
    unittest.main()
