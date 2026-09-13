import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk.engine.framebuffer import FrameBuffer
from citywalk.renderer import renderer, sky
from citywalk.renderer.camera import Camera
from citywalk.world import gen
from citywalk.world.grid import TYPE_TABLE


class TestFrameBufferSmoke(unittest.TestCase):
    def test_sixty_frames_render_valid_buffer(self):
        grid, lights, spawn = gen.build()
        stars = sky.make_stars(1)
        moon = (0.72, 0.16)
        cam = Camera(spawn[0], spawn[1], spawn[2])
        W, H = 100, 40
        fb = FrameBuffer(W, H)
        for f in range(60):
            cam.turn(0.03)
            # safe forward step with a collision guard
            nx, ny = cam.x + cam.dir_x * 0.05, cam.y + cam.dir_y * 0.05
            if not grid.is_solid(int(nx), int(ny)):
                cam.x, cam.y = nx, ny
            renderer.render_frame(fb, cam, grid, lights, stars, moon, TYPE_TABLE)
            ansi = fb.to_ansi("truecolor")
            self.assertIsInstance(ansi, str)
            self.assertGreater(len(ansi), 0)
            self.assertTrue(ansi.startswith("\x1b[H"))

        for y in range(H):
            for x in range(W):
                i = y * W + x
                g = fb.glyph[i]
                self.assertTrue(32 <= g <= 126, (x, y, g))
                j = i * 3
                for k in range(3):
                    self.assertTrue(0 <= fb.fg[j + k] <= 255)
                    self.assertTrue(0 <= fb.bg[j + k] <= 255)

    def test_ansi_256_fallback(self):
        grid, lights, spawn = gen.build()
        stars = sky.make_stars(1)
        moon = (0.72, 0.16)
        cam = Camera(spawn[0], spawn[1], spawn[2])
        fb = FrameBuffer(60, 24)
        renderer.render_frame(fb, cam, grid, lights, stars, moon, TYPE_TABLE)
        ansi = fb.to_ansi("256")
        self.assertIn("\x1b[38;5;", ansi)


if __name__ == "__main__":
    unittest.main()
