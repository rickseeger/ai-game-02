import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import citywalk.config as config
from citywalk.renderer import dda
from citywalk.renderer.camera import Camera
from citywalk.world.grid import Grid


def wall_grid(w=12, h=12, cells=()):
    g = Grid(w, h)
    for (x, y) in cells:
        g.set(x, y, 1, height=1)
    return g


class TestDDA(unittest.TestCase):
    def test_straight_ahead_hits_cell_and_side(self):
        g = wall_grid(cells=[(5, 5)])
        cam = Camera(2.5, 5.5, 0.0)
        hit = dda.cast_ray(g, cam.x, cam.y, cam.dir_x, cam.dir_y,
                           cam.plane_x, cam.plane_y, 0.0, config.MAX_DDA_STEPS)
        self.assertIsNotNone(hit)
        side, mx, my, d, rdx, rdy = hit
        self.assertEqual((mx, my), (5, 5))
        self.assertEqual(side, 0)
        self.assertAlmostEqual(d, 2.5, places=5)

    def test_y_face_hit_and_distance(self):
        g = wall_grid(cells=[(5, 7)])
        cam = Camera(5.5, 3.5, math.pi / 2.0)
        hit = dda.cast_ray(g, cam.x, cam.y, cam.dir_x, cam.dir_y,
                           cam.plane_x, cam.plane_y, 0.0, config.MAX_DDA_STEPS)
        self.assertIsNotNone(hit)
        side, mx, my, d, rdx, rdy = hit
        self.assertEqual((mx, my), (5, 7))
        self.assertEqual(side, 1)
        self.assertAlmostEqual(d, 3.5, places=5)

    def test_diagonal_perpendicular_distance(self):
        # camera at (1.5, 1.5) facing 45 deg hits the wall at x=4
        g = wall_grid(cells=[(4, 4)])
        cam = Camera(1.5, 1.5, math.pi / 4.0)
        hit = dda.cast_ray(g, cam.x, cam.y, cam.dir_x, cam.dir_y,
                           cam.plane_x, cam.plane_y, 0.0, config.MAX_DDA_STEPS)
        self.assertIsNotNone(hit)
        side, mx, my, d, rdx, rdy = hit
        # perpendicular distance to the x=4 plane from (1.5,1.5) along a 45deg ray
        self.assertAlmostEqual(d, 2.5 / math.cos(math.pi / 4.0), places=4)

    def test_open_grid_terminates(self):
        g = Grid(10, 10)
        cam = Camera(5.5, 5.5, 0.0)
        hit = dda.cast_ray(g, cam.x, cam.y, cam.dir_x, cam.dir_y,
                           cam.plane_x, cam.plane_y, 0.0, 32)
        self.assertIsNone(hit)

    def test_camera_plane_orientation(self):
        # camera_x=+1 (right column) points dir + plane; at angle 0 plane is +y
        cam = Camera(1.5, 1.5, 0.0)
        rdx = cam.dir_x + cam.plane_x * 1.0
        rdy = cam.dir_y + cam.plane_y * 1.0
        self.assertGreater(rdx, 0.0)
        self.assertGreater(rdy, 0.0)

    def test_face_u_in_unit_range(self):
        g = wall_grid(cells=[(5, 5)])
        cam = Camera(2.5, 5.5, 0.0)
        hit = dda.cast_ray(g, cam.x, cam.y, cam.dir_x, cam.dir_y,
                           cam.plane_x, cam.plane_y, 0.0, config.MAX_DDA_STEPS)
        side, mx, my, d, rdx, rdy = hit
        u = dda.face_u(side, cam.x, cam.y, d, rdx, rdy)
        self.assertGreaterEqual(u, 0.0)
        self.assertLess(u, 1.0)


if __name__ == "__main__":
    unittest.main()
