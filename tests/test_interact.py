"""Interaction gating tests (node 5): eat/drink only at valid vendor locations.

The interactor derives a vendor "serving footprint" (awnings, tables, chairs)
from the generated restaurants and only lets a player eat/drink within
INTERACT_RANGE of one of those cells -- i.e. only when physically stopped at a
restaurant/vendor, never from across the map. Also asserts every vendor is
actually reachable from spawn so the loop can never ask for the impossible.
"""
import os
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk import config
from citywalk.world import gen
from citywalk.world.interact import Interactor
from citywalk.world.survival import Needs


def _reachable(grid, start):
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


class TestVendorFootprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = gen.generate(seed=20260913)
        cls.grid = cls.city.grid
        cls.inter = Interactor(cls.city.grid, cls.city.restaurants)

    def test_footprint_is_nonempty(self):
        self.assertGreater(len(self.inter.vendor_cells), 0)
        self.assertGreaterEqual(len(self.city.restaurants), 6)

    def test_at_vendor_standing_on_a_table(self):
        # every restaurant exposes a serving cell the player can stand at
        for r in self.city.restaurants:
            served = r.tables + r.chairs + r.awning
            self.assertGreater(len(served), 0, (r.x, r.y))
            tx, ty = served[0]
            self.assertTrue(self.inter.at_vendor(tx + 0.5, ty + 0.5),
                            (r.x, r.y, tx, ty))

    def test_not_at_vendor_from_across_the_map(self):
        # top-left border cell, far from any downtown/midtown restaurant
        self.assertFalse(self.inter.at_vendor(2.5, 2.5))

    def test_spawn_is_not_on_top_of_a_vendor(self):
        # the plaza spawn is a walk from the nearest vendor, not inside it
        x, y = self.city.spawn[0], self.city.spawn[1]
        self.assertFalse(self.inter.at_vendor(x, y), (x, y))

    def test_every_vendor_is_reachable_from_spawn(self):
        seen = _reachable(self.grid, self.city.spawn)
        for (vx, vy) in self.inter.vendor_cells:
            self.assertIn((vx, vy), seen, (vx, vy))
            self.assertFalse(self.grid.is_solid(vx, vy), (vx, vy))


class TestEatDrinkGating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = gen.generate(seed=20260913)
        cls.inter = Interactor(cls.city.grid, cls.city.restaurants)

    def _a_vendor_spot(self):
        r = self.city.restaurants[0]
        tx, ty = (r.tables + r.chairs + r.awning)[0]
        return tx + 0.5, ty + 0.5

    def test_eat_at_vendor_replenishes_and_costs(self):
        n = Needs(hunger=50.0, credits=40)
        x, y = self._a_vendor_spot()
        self.assertTrue(self.inter.try_eat(n, x, y))
        self.assertGreater(n.hunger, 50.0)
        self.assertEqual(n.credits, 40 - config.MEAL_COST)

    def test_drink_at_vendor_replenishes_and_costs(self):
        n = Needs(thirst=40.0, credits=40)
        x, y = self._a_vendor_spot()
        self.assertTrue(self.inter.try_drink(n, x, y))
        self.assertGreater(n.thirst, 40.0)
        self.assertEqual(n.credits, 40 - config.DRINK_COST)

    def test_eat_far_from_vendor_is_refused_without_effect(self):
        n = Needs(hunger=50.0, credits=40)
        self.assertFalse(self.inter.try_eat(n, 2.5, 2.5))
        self.assertEqual(n.hunger, 50.0)
        self.assertEqual(n.thirst, 100.0)
        self.assertEqual(n.credits, 40)
        self.assertEqual(n.message, "find a restaurant to eat")

    def test_drink_far_from_vendor_is_refused_without_effect(self):
        n = Needs(thirst=40.0, credits=40)
        self.assertFalse(self.inter.try_drink(n, 2.5, 2.5))
        self.assertEqual(n.thirst, 40.0)
        self.assertEqual(n.credits, 40)
        self.assertEqual(n.message, "find a vendor to buy a drink")


if __name__ == "__main__":
    unittest.main()
