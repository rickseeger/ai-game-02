"""Moving city life tests (node 4): determinism, terrain containment,
continuous motion, and sprite projection / rendering.

Covers the movement/AI logic directly (cars stay on asphalt, pedestrians on
sidewalk/cobble, pets on sidewalk/cobble/grass) and the renderer integration
(the life system runs headless against the framebuffer without breaking it).
"""
import math
import os
import random
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk.engine.framebuffer import FrameBuffer
from citywalk.renderer import renderer, sky, sprites
from citywalk.renderer.camera import Camera
from citywalk.world import gen
from citywalk.world.entities import (LifeSystem, Entity, CAR, PEDESTRIAN, PET,
                                     WALKABLE)
from citywalk.world.grid import Grid, TYPE_TABLE, GRASS


def _step(life, seconds=40.0, fps=30.0):
    n = int(seconds * fps)
    dt = 1.0 / fps
    for _ in range(n):
        life.update(dt)


class TestLifeDeterminism(unittest.TestCase):
    def test_same_seed_same_population(self):
        grid, _, _ = gen.build(seed=7)
        a = LifeSystem(grid, seed=7)
        b = LifeSystem(grid, seed=7)
        self.assertEqual(len(a.entities), len(b.entities))
        for ea, eb in zip(a.entities, b.entities):
            self.assertEqual(ea.kind, eb.kind)
            self.assertEqual(ea.color, eb.color)
            self.assertEqual(ea.dir, eb.dir)
            self.assertAlmostEqual(ea.x, eb.x, places=12)
            self.assertAlmostEqual(ea.y, eb.y, places=12)
            self.assertAlmostEqual(ea.speed, eb.speed, places=12)

    def test_different_seed_differs(self):
        grid, _, _ = gen.build(seed=7)
        a = LifeSystem(grid, seed=7)
        b = LifeSystem(grid, seed=8)
        self.assertNotEqual([(e.x, e.y) for e in a.entities],
                            [(e.x, e.y) for e in b.entities])

    def test_simulation_is_deterministic(self):
        grid, _, _ = gen.build(seed=7)
        a = LifeSystem(grid, seed=7)
        b = LifeSystem(grid, seed=7)
        _step(a, seconds=20.0)
        _step(b, seconds=20.0)
        pa = [(e.kind, round(e.x, 9), round(e.y, 9)) for e in a.entities]
        pb = [(e.kind, round(e.x, 9), round(e.y, 9)) for e in b.entities]
        self.assertEqual(pa, pb)


class TestLifeContainment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid, cls.lights, _ = gen.build(seed=20260913)
        cls.life = LifeSystem(cls.grid, seed=20260913)
        _step(cls.life, seconds=40.0)

    def test_population_is_nonempty_and_mixed(self):
        kinds = {}
        for e in self.life.entities:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        self.assertGreaterEqual(kinds.get(CAR, 0), 5, kinds)
        self.assertGreaterEqual(kinds.get(PEDESTRIAN, 0), 5, kinds)
        self.assertGreaterEqual(len(self.life.entities), 20)

    def test_every_entity_stays_on_its_terrain(self):
        for e in self.life.entities:
            cx, cy = int(e.x), int(e.y)
            self.assertTrue(self.grid.in_bounds(cx, cy), (e.kind, cx, cy))
            t = self.grid.type_of(cx, cy)
            self.assertIn(t, WALKABLE[e.kind],
                          "kind=%s at (%d,%d) type=%d" % (e.kind, cx, cy, t))

    def test_positions_finite_and_in_bounds(self):
        for e in self.life.entities:
            self.assertTrue(math.isfinite(e.x) and math.isfinite(e.y))
            self.assertTrue(math.isfinite(e.z))
            self.assertTrue(0.0 <= e.x < self.grid.w, e.x)
            self.assertTrue(0.0 <= e.y < self.grid.h, e.y)

    def test_entities_actually_move(self):
        grid, _, _ = gen.build(seed=20260913)
        life = LifeSystem(grid, seed=20260913)
        starts = [(int(e.x), int(e.y)) for e in life.entities]
        _step(life, seconds=40.0)
        moved = sum(1 for e, s in zip(life.entities, starts)
                    if (int(e.x), int(e.y)) != s)
        self.assertGreater(moved, len(life.entities) * 0.5, moved)


class TestSpriteProjection(unittest.TestCase):
    def test_project_straight_ahead(self):
        cam = Camera(10.0, 10.0, 0.0)   # facing +x
        tx, ty = sprites.project(cam, 15.0, 10.0)
        self.assertAlmostEqual(ty, 5.0, places=5)   # five cells ahead
        self.assertAlmostEqual(tx, 0.0, places=5)   # dead ahead -> screen center

    def test_project_behind_camera_returns_none(self):
        cam = Camera(10.0, 10.0, 0.0)
        self.assertIsNone(sprites.project(cam, 5.0, 10.0))

    def test_project_right_of_view_is_positive(self):
        cam = Camera(10.0, 10.0, 0.0)
        tx, ty = sprites.project(cam, 12.0, 11.0)
        self.assertGreater(ty, 0.0)
        self.assertGreater(tx, 0.0)


class TestLifeRendering(unittest.TestCase):
    def _flat_grid(self, w=24, h=24):
        g = Grid(w, h)
        for y in range(h):
            for x in range(w):
                g.set(x, y, GRASS)
        return g

    def test_render_with_life_produces_valid_buffer(self):
        grid, lights, spawn = gen.build(seed=20260913)
        life = LifeSystem(grid, seed=20260913)
        stars = sky.make_stars(1)
        moon = (0.72, 0.16)
        cam = Camera(spawn[0], spawn[1], spawn[2])
        fb = FrameBuffer(120, 40)
        for _ in range(30):
            life.update(1.0 / 30.0)
            cam.turn(0.05)
            renderer.render_frame(fb, cam, grid, lights, stars, moon,
                                  TYPE_TABLE, life)
            ansi = fb.to_ansi("truecolor")
            self.assertTrue(ansi.startswith("\x1b[H"))
        for y in range(40):
            for x in range(120):
                i = y * 120 + x
                self.assertTrue(32 <= fb.glyph[i] <= 126, (x, y))
                j = i * 3
                for k in range(3):
                    self.assertTrue(0 <= fb.fg[j + k] <= 255)
                    self.assertTrue(0 <= fb.bg[j + k] <= 255)

    def test_car_billboard_drawn_in_front_of_camera(self):
        g = self._flat_grid()
        cam = Camera(10.5, 10.5, 0.0)   # facing +x over open ground
        car = Entity(CAR, 14.5, 10.5, 0.0, 1, 2.0, "car_taxi", "#",
                     random.Random(1), ax=14, ay=10, bx=14, by=10,
                     t=0.0, pause=0.0)
        life = SimpleNamespace(entities=[car])
        fb = FrameBuffer(120, 40)
        renderer.render_frame(fb, cam, g, [], sky.make_stars(1), (0.72, 0.16),
                              TYPE_TABLE, life)
        # the car body glyph should appear somewhere in the floor half
        hits = [1 for y in range(20, 40) for x in range(120)
                if chr(fb.glyph[y * 120 + x]) in ("#", ":", "*")]
        self.assertGreater(sum(hits), 0)

    def test_wall_occludes_sprite_via_zbuffer(self):
        # a solid wall directly in front, a car behind it -> car is hidden
        g = self._flat_grid()
        for yy in range(0, 24):
            g.set(12, yy, 1, height=6)   # solid wall column at x=12
        cam = Camera(10.5, 10.5, 0.0)   # facing +x toward the wall
        car = Entity(CAR, 16.5, 10.5, 0.0, 1, 2.0, "car_taxi", "#",
                     random.Random(1), ax=16, ay=10, bx=16, by=10,
                     t=0.0, pause=0.0)
        life = SimpleNamespace(entities=[car])
        fb = FrameBuffer(120, 40)
        renderer.render_frame(fb, cam, g, [], sky.make_stars(1), (0.72, 0.16),
                              TYPE_TABLE, life)
        # no car body glyph should appear (the wall occludes it)
        hits = [1 for y in range(20, 40) for x in range(120)
                if chr(fb.glyph[y * 120 + x]) in ("#", ":", "*")]
        self.assertEqual(sum(hits), 0)


if __name__ == "__main__":
    unittest.main()
