import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import citywalk.config as config
from citywalk.renderer import floorcast
from citywalk.renderer.camera import Camera


class TestFloorcast(unittest.TestCase):
    def test_center_row_projects_straight_ahead(self):
        cam = Camera(10.0, 10.0, 0.0)
        W, H = 99, 40  # odd width -> column 49 is exactly the center (t == 0.5)
        horizon = H // 2
        wx, wy, rd = floorcast.inverse_project(cam, W // 2, horizon + 10,
                                               horizon, W, H)
        # straight ahead = +x direction at angle 0 -> wy stays 10.0
        self.assertAlmostEqual(wy, 10.0, places=5)
        self.assertGreater(wx, 10.0)
        self.assertAlmostEqual(rd, config.EYE_HEIGHT * H / 10.0, places=6)

    def test_near_rows_have_greater_distance_step(self):
        cam = Camera(0.0, 0.0, 0.0)
        W, H = 100, 40
        horizon = H // 2
        near = floorcast.inverse_project(cam, W // 2, horizon + 2, horizon, W, H)[2]
        far = floorcast.inverse_project(cam, W // 2, horizon + 20, horizon, W, H)[2]
        self.assertGreater(near, far)

    def test_horizon_row_returns_none(self):
        cam = Camera(0.0, 0.0, 0.0)
        self.assertIsNone(floorcast.inverse_project(cam, 50, 20, 20, 100, 40))

    def test_edges_symmetric_about_center(self):
        cam = Camera(5.0, 5.0, 0.0)
        W, H = 100, 40
        horizon = H // 2
        left = floorcast.inverse_project(cam, 0, horizon + 10, horizon, W, H)
        right = floorcast.inverse_project(cam, W - 1, horizon + 10, horizon, W, H)
        # symmetric y offsets about the facing direction
        self.assertAlmostEqual(left[1], 5.0 - (right[1] - 5.0), places=3)


if __name__ == "__main__":
    unittest.main()
