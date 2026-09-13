"""Unit tests for the top-down renderer and camera (node G10/6).

Verifies the invariants required by the completion contract:

1. the frame buffer maps each cell to a single char plus optional ANSI
   256-color foreground/background, and serializes with minimal escapes;
2. the camera windows a viewport onto the world, centered on the player and
   clamped to the map edge;
3. the scene renderer composes the city grid, building facades, and player
   into a colored frame of exactly the viewport's dimensions;
4. the player stays centered in the viewport as the camera follows it;
5. rendering is deterministic and the player glyph lands at the right cell.
"""

import unittest

from citywalk2d.renderer import (
    Camera,
    Cell,
    FrameBuffer,
    PLAYER_GLYPH,
    RESET,
    render,
    render_frame,
    scheme_to_256,
    sgr,
    strip_ansi,
)
from citywalk2d.world import (
    SCHEMES,
    ColorScheme,
    Player,
    assign_facades,
    generate_city,
    spawn_player,
)


def central_street(grid):
    """The street cell closest to the map center (for camera-centering tests)."""
    cx, cy = grid.width // 2, grid.height // 2
    best = None
    for x, y in grid.street_cells():
        d = abs(x - cx) + abs(y - cy)
        if best is None or d < best[0]:
            best = (d, (x, y))
    return best[1]


def player_view_pos(plain_frame):
    """The (x, y) cell of the player glyph in a stripped frame, or None."""
    for y, line in enumerate(plain_frame.split("\n")):
        x = line.find(PLAYER_GLYPH)
        if x != -1:
            return (x, y)
    return None


class TestSgr(unittest.TestCase):
    def test_no_color_yields_empty(self):
        self.assertEqual(sgr(), "")
        self.assertEqual(sgr(None, None), "")

    def test_foreground_only(self):
        self.assertEqual(sgr(196), "\x1b[38;5;196m")

    def test_background_only(self):
        self.assertEqual(sgr(bg=226), "\x1b[48;5;226m")

    def test_both_colors_combined(self):
        self.assertEqual(sgr(16, 226), "\x1b[38;5;16;48;5;226m")

    def test_rejects_out_of_range_and_bool(self):
        for bad in (256, -1, 300, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sgr(bad)
                with self.assertRaises(ValueError):
                    sgr(bg=bad)

    def test_strip_ansi(self):
        self.assertEqual(strip_ansi("\x1b[38;5;196m@\x1b[0m"), "@")
        self.assertEqual(strip_ansi("plain"), "plain")


class TestCell(unittest.TestCase):
    def test_defaults(self):
        cell = Cell()
        self.assertEqual(cell.char, " ")
        self.assertIsNone(cell.fg)
        self.assertIsNone(cell.bg)

    def test_rejects_multichar(self):
        with self.assertRaises(ValueError):
            Cell("ab")

    def test_rejects_bad_color(self):
        with self.assertRaises(ValueError):
            Cell("x", fg=256)
        with self.assertRaises(ValueError):
            Cell("x", bg=-1)

    def test_immutable(self):
        cell = Cell("x", fg=1, bg=2)
        with self.assertRaises(AttributeError):
            cell.char = "y"


class TestFrameBuffer(unittest.TestCase):
    def test_dimensions_and_default_fill(self):
        fb = FrameBuffer(3, 2)
        self.assertEqual((fb.width, fb.height), (3, 2))
        for x in range(3):
            for y in range(2):
                self.assertEqual(fb.get(x, y), Cell())

    def test_set_get_roundtrip(self):
        fb = FrameBuffer(2, 2)
        cell = Cell("@", fg=196, bg=226)
        fb.set(1, 0, cell)
        self.assertEqual(fb.get(1, 0), cell)

    def test_out_of_bounds_raises(self):
        fb = FrameBuffer(2, 2)
        with self.assertRaises(IndexError):
            fb.get(-1, 0)
        with self.assertRaises(IndexError):
            fb.get(2, 0)
        with self.assertRaises(IndexError):
            fb.set(0, 2, Cell())

    def test_set_rejects_non_cell(self):
        fb = FrameBuffer(2, 2)
        with self.assertRaises(TypeError):
            fb.set(0, 0, "@")

    def test_render_plain_has_no_escapes(self):
        fb = FrameBuffer(2, 1)
        fb.set(0, 0, Cell("@", fg=196))
        fb.set(1, 0, Cell("x", bg=226))
        self.assertEqual(fb.render(color=False), "@x")
        self.assertNotIn("\x1b", fb.render(color=False))

    def test_render_single_foreground_cell(self):
        fb = FrameBuffer(1, 1)
        fb.set(0, 0, Cell("@", fg=196))
        self.assertEqual(fb.render(), "\x1b[38;5;196m@\x1b[0m")

    def test_render_single_background_cell(self):
        fb = FrameBuffer(1, 1)
        fb.set(0, 0, Cell(" ", bg=226))
        self.assertEqual(fb.render(), "\x1b[48;5;226m \x1b[0m")

    def test_render_single_cell_both_colors(self):
        fb = FrameBuffer(1, 1)
        fb.set(0, 0, Cell("@", 16, 226))
        self.assertEqual(fb.render(), "\x1b[38;5;16;48;5;226m@\x1b[0m")

    def test_render_reuses_color_for_run(self):
        fb = FrameBuffer(2, 1)
        fb.set(0, 0, Cell("a", fg=196))
        fb.set(1, 0, Cell("b", fg=196))
        self.assertEqual(fb.render(), "\x1b[38;5;196mab\x1b[0m")

    def test_render_resets_on_transition_to_plain(self):
        fb = FrameBuffer(2, 1)
        fb.set(0, 0, Cell("@", fg=196))
        fb.set(1, 0, Cell(" "))
        self.assertEqual(fb.render(), "\x1b[38;5;196m@\x1b[0m ")

    def test_render_line_geometry(self):
        fb = FrameBuffer(3, 2)
        lines = fb.render(color=False).split("\n")
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(len(line), 3)


class TestCamera(unittest.TestCase):
    def test_centers_on_middle_of_large_world(self):
        cam = Camera.centered_on(32, 22, 40, 20, 64, 44)
        self.assertEqual((cam.x, cam.y), (12, 12))
        self.assertTrue(cam.centers(32, 22))

    def test_clamps_to_top_left(self):
        cam = Camera.centered_on(2, 2, 40, 20, 64, 44)
        self.assertEqual((cam.x, cam.y), (0, 0))
        self.assertFalse(cam.centers(2, 2))

    def test_clamps_to_bottom_right(self):
        cam = Camera.centered_on(62, 42, 40, 20, 64, 44)
        self.assertEqual((cam.x, cam.y), (24, 24))
        self.assertFalse(cam.centers(62, 42))

    def test_viewport_larger_than_world_centers_world(self):
        cam = Camera.centered_on(10, 10, 80, 60, 64, 44)
        # Origin goes negative so the whole world is centered in the viewport.
        self.assertEqual((cam.x, cam.y), (-8, -8))
        # World corners land inside the viewport, symmetric margins of 8 cells.
        self.assertEqual(cam.world_to_view(0, 0), (8, 8))
        self.assertEqual(cam.world_to_view(63, 43), (71, 51))
        self.assertTrue(cam.contains_world(0, 0))
        self.assertTrue(cam.contains_world(63, 43))

    def test_world_view_roundtrip(self):
        cam = Camera.centered_on(32, 22, 40, 20, 64, 44)
        vx, vy = cam.world_to_view(32, 22)
        self.assertEqual((vx, vy), (20, 10))
        self.assertEqual(cam.view_to_world(vx, vy), (32, 22))

    def test_window_property(self):
        cam = Camera(40, 20, 64, 44, 12, 12)
        self.assertEqual(cam.window, (12, 12, 52, 32))


class TestSchemeTo256(unittest.TestCase):
    def test_known_schemes(self):
        cases = {
            "brick_red": (15, 1),
            "ocean": (0, 6),
            "sunshine": (0, 3),
            "forest": (15, 2),
            "royal": (15, 4),
            "grape": (15, 5),
            "graphite": (15, 8),
            "porcelain": (0, 15),
        }
        by_name = {scheme.name: scheme for scheme in SCHEMES}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertIn(name, by_name)
                self.assertEqual(scheme_to_256(by_name[name]), expected)

    def test_unknown_code_treated_as_none(self):
        scheme = ColorScheme("weird", "99", "123")
        self.assertEqual(scheme_to_256(scheme), (None, None))


class TestRenderFrame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = generate_city(width=64, height=44, seed=12345)
        cls.facades = assign_facades(cls.city)
        cls.player = spawn_player(cls.city, seed=7)

    def test_full_render_matches_city_dimensions(self):
        frame = render(
            self.city, self.facades, self.player,
            viewport_width=self.city.width, viewport_height=self.city.height,
            color=False,
        )
        lines = frame.split("\n")
        self.assertEqual(len(lines), self.city.height)
        for line in lines:
            self.assertEqual(len(line), self.city.width)

    def test_full_render_is_colored(self):
        frame = render(
            self.city, self.facades, self.player,
            viewport_width=self.city.width, viewport_height=self.city.height,
        )
        self.assertIn("\x1b[", frame)

    def test_street_and_interior_are_painted(self):
        frame = render(
            self.city, self.facades, self.player,
            viewport_width=self.city.width, viewport_height=self.city.height,
        )
        self.assertIn("\x1b[48;5;236m", frame)  # asphalt streets
        self.assertIn("\x1b[48;5;238m", frame)  # concrete block interiors

    def test_player_drawn_at_exact_world_position(self):
        frame = render(
            self.city, self.facades, self.player,
            viewport_width=self.city.width, viewport_height=self.city.height,
            color=False,
        )
        self.assertEqual(player_view_pos(frame), self.player.position)

    def test_render_is_deterministic(self):
        a = render(self.city, self.facades, self.player, viewport_width=30, viewport_height=15)
        b = render(self.city, self.facades, self.player, viewport_width=30, viewport_height=15)
        self.assertEqual(a, b)

    def test_viewport_geometry(self):
        frame = render(self.city, self.facades, self.player, viewport_width=40, viewport_height=20, color=False)
        lines = frame.split("\n")
        self.assertEqual(len(lines), 20)
        for line in lines:
            self.assertEqual(len(line), 40)


class TestCameraFollowsPlayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = generate_city(width=64, height=44, seed=12345)
        cls.facades = assign_facades(cls.city)

    def test_player_centered_in_viewport(self):
        x, y = central_street(self.city)
        player = Player(self.city, x, y)
        frame = render(self.city, self.facades, player, viewport_width=20, viewport_height=10, color=False)
        self.assertEqual(player_view_pos(frame), (10, 5))

    def test_camera_follows_shifted_player(self):
        x, y = central_street(self.city)
        # A second central street cell a little to the right, same row.
        candidates = [(xx, yy) for (xx, yy) in self.city.street_cells() if yy == y and xx > x]
        self.assertTrue(candidates, "expected another street cell on the same row")
        nx = candidates[0][0]
        for player in (Player(self.city, x, y), Player(self.city, nx, y)):
            frame = render(self.city, self.facades, player, viewport_width=20, viewport_height=10, color=False)
            self.assertEqual(player_view_pos(frame), (10, 5))

    def test_camera_clamps_near_edge(self):
        # (0, 0) is a guaranteed street cell at the map's corner.
        player = Player(self.city, 0, 0)
        frame = render(self.city, self.facades, player, viewport_width=20, viewport_height=10, color=False)
        self.assertEqual(player_view_pos(frame), (0, 0))


if __name__ == "__main__":
    unittest.main()
