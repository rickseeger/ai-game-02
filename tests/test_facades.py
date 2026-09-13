"""Unit tests for the building facade layer (node G10/3).

Verifies the facade invariants required by the completion contract:

1. every building is assigned a facade
2. facade strings fit their building's bounds exactly
3. a seeded city shows variety (multiple distinct facades and colors)
4. assignment is deterministic (same seed -> identical, different seed -> different)
5. the sample colored render emits ANSI colors and keeps grid geometry
"""

import re
import unittest

from citywalk2d.world import (
    ColorScheme,
    Facade,
    PATTERNS,
    SCHEMES,
    assign_facades,
    generate_city,
    render_colored_city,
)


def facade_signature(facade_map):
    """Deterministic, comparable description of a whole facade assignment."""
    return [(f.name, f.scheme.name) for f in facade_map.facades]


class TestFacadeAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = generate_city(width=48, height=32, seed=12345)
        cls.facades = assign_facades(cls.city)

    def test_every_building_has_a_facade(self):
        self.assertEqual(len(self.facades), len(self.city.buildings))
        for b in self.city.buildings:
            f = self.facades.facade_for(b.id)
            self.assertIsInstance(f, Facade)
            self.assertIn(f.name, PATTERNS)
            self.assertIsInstance(f.scheme, ColorScheme)
            self.assertIn(f.scheme, SCHEMES)

    def test_facade_strings_fit_building_bounds(self):
        for b in self.city.buildings:
            f = self.facades.facade_for(b.id)
            rows = f.render(b.rect.w, b.rect.h)
            self.assertEqual(len(rows), b.rect.h)
            for row in rows:
                self.assertEqual(len(row), b.rect.w)

    def test_variety_multiple_facades_and_colors(self):
        names = {f.name for f in self.facades.facades}
        schemes = {f.scheme.name for f in self.facades.facades}
        self.assertGreaterEqual(len(names), 2)
        self.assertGreaterEqual(len(schemes), 2)

    def test_no_immediate_repeat_across_consecutive_buildings(self):
        seq = list(self.facades.facades)
        self.assertGreater(len(seq), 1)
        for a, b in zip(seq, seq[1:]):
            self.assertNotEqual(a.name, b.name)
            self.assertNotEqual(a.scheme.name, b.scheme.name)


class TestFacadeDeterminism(unittest.TestCase):
    def test_same_seed_reproduces_identical_facades(self):
        city = generate_city(width=48, height=32, seed=777)
        a = assign_facades(city, seed=11)
        b = assign_facades(city, seed=11)
        self.assertEqual(facade_signature(a), facade_signature(b))

    def test_different_seed_differs(self):
        city = generate_city(width=48, height=32, seed=777)
        a = assign_facades(city, seed=11)
        b = assign_facades(city, seed=12)
        self.assertNotEqual(facade_signature(a), facade_signature(b))

    def test_defaults_to_city_seed(self):
        city = generate_city(width=48, height=32, seed=777)
        a = assign_facades(city)
        b = assign_facades(city, seed=777)
        self.assertEqual(facade_signature(a), facade_signature(b))


class TestSampleRender(unittest.TestCase):
    def test_colored_city_render(self):
        city = generate_city(width=48, height=32, seed=12345)
        facades = assign_facades(city)
        text = render_colored_city(city, facades)
        # color sequences are present
        self.assertIn("\x1b[", text)
        # stripping escapes leaves the exact grid geometry
        plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
        lines = plain.split("\n")
        self.assertEqual(len(lines), city.height)
        for line in lines:
            self.assertEqual(len(line), city.width)


if __name__ == "__main__":
    unittest.main()
