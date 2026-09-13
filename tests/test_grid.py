"""Unit tests for the city grid model (node G10/2).

Verifies the grid invariants required by the completion contract:

1. streets form a single connected walkable graph
2. buildings never overlap one another
3. buildings stay inside their block and inside the map bounds
4. every street cell is walkable, and no building cell is walkable
5. generation is deterministic (same seed -> identical layout)
"""

import itertools
import unittest

from citywalk2d.world import CellType, generate_city


def rects_overlap(a, b):
    """True if two Rects share any cell."""
    return not (a.x2 <= b.x or b.x2 <= a.x or a.y2 <= b.y or b.y2 <= a.y)


class TestCityGridInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = generate_city(width=48, height=32, seed=12345)

    def test_has_blocks_and_buildings(self):
        self.assertGreaterEqual(len(self.grid.blocks), 1)
        self.assertGreaterEqual(len(self.grid.buildings), 1)

    def test_streets_form_connected_graph(self):
        g = self.grid
        streets = list(g.street_cells())
        self.assertTrue(streets, "city must contain street cells")
        start = streets[0]
        seen = set()
        stack = [start]
        while stack:
            x, y = stack.pop()
            if (x, y) in seen:
                continue
            seen.add((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if g.in_bounds(nx, ny) and g.cell_type(nx, ny) == CellType.STREET:
                    stack.append((nx, ny))
        self.assertEqual(
            seen, set(streets),
            "all street cells must be reachable from one another",
        )

    def test_every_street_cell_is_walkable(self):
        for x, y in self.grid.street_cells():
            self.assertTrue(self.grid.is_walkable(x, y))

    def test_buildings_do_not_overlap(self):
        buildings = self.grid.buildings
        for a, b in itertools.combinations(buildings, 2):
            self.assertFalse(
                rects_overlap(a.rect, b.rect),
                f"buildings {a.id} and {b.id} overlap",
            )

    def test_buildings_within_bounds(self):
        g = self.grid
        for b in g.buildings:
            self.assertGreaterEqual(b.rect.x, 0)
            self.assertGreaterEqual(b.rect.y, 0)
            self.assertLessEqual(b.rect.x2, g.width)
            self.assertLessEqual(b.rect.y2, g.height)

    def test_buildings_within_their_block(self):
        g = self.grid
        for b in g.buildings:
            block = g.block_by_id(b.block_id)
            inside = (
                block.rect.x <= b.rect.x
                and block.rect.y <= b.rect.y
                and b.rect.x2 <= block.rect.x2
                and b.rect.y2 <= block.rect.y2
            )
            self.assertTrue(inside, f"building {b.id} escapes block {b.block_id}")

    def test_building_at_roundtrip(self):
        g = self.grid
        for b in g.buildings:
            for x, y in b.rect.cells():
                found = g.building_at(x, y)
                self.assertIsNotNone(found)
                self.assertEqual(found.id, b.id)
        for x, y in g.street_cells():
            self.assertIsNone(g.building_at(x, y))

    def test_no_building_cell_is_walkable(self):
        for b in self.grid.buildings:
            for x, y in b.rect.cells():
                self.assertFalse(self.grid.is_walkable(x, y))

    def test_interior_cells_exist_and_are_inert(self):
        g = self.grid
        interiors = [
            (x, y)
            for y in range(g.height)
            for x in range(g.width)
            if g.cell_type(x, y) == CellType.INTERIOR
        ]
        self.assertTrue(interiors, "expected some block-interior cells")
        for x, y in interiors:
            self.assertFalse(g.is_walkable(x, y))
            self.assertIsNone(g.building_at(x, y))

    def test_out_of_bounds_queries(self):
        g = self.grid
        self.assertFalse(g.is_walkable(-1, 0))
        self.assertFalse(g.is_walkable(0, g.height))
        self.assertIsNone(g.building_at(-1, 0))
        with self.assertRaises(IndexError):
            g.cell_type(-1, 0)

    def test_render_dimensions_and_glyphs(self):
        g = self.grid
        text = g.render()
        lines = text.split("\n")
        self.assertEqual(len(lines), g.height)
        for line in lines:
            self.assertEqual(len(line), g.width)
            self.assertTrue(set(line) <= {"#", ".", " "})


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_layout(self):
        a = generate_city(width=48, height=32, seed=999)
        b = generate_city(width=48, height=32, seed=999)
        a_cells = [a.cell_type(x, y) for y in range(a.height) for x in range(a.width)]
        b_cells = [b.cell_type(x, y) for y in range(b.height) for x in range(b.width)]
        self.assertEqual(a_cells, b_cells)
        self.assertEqual([b.rect for b in a.buildings], [b.rect for b in b.buildings])

    def test_different_seed_different_layout(self):
        a = generate_city(width=48, height=32, seed=1)
        b = generate_city(width=48, height=32, seed=2)
        self.assertNotEqual([b.rect for b in a.buildings], [b.rect for b in b.buildings])


if __name__ == "__main__":
    unittest.main()
