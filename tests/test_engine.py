"""Integration tests for the assembled game loop (node G10/7).

Verifies the completion contract: the grid, facades, movement, input, and
renderer are wired into a single running loop that

1. renders the viewport before and after every step,
2. advances the player one cell per movement action,
3. stops cleanly on QUIT (or when a script runs out),
4. drives a scripted walk through the city without error.

The interactive terminal path (raw key reading) needs a real keyboard and is
confirmed live by Rick; these tests drive the same core loop with a scripted
sequence of actions instead.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from citywalk2d import __main__ as entrypoint
from citywalk2d.engine import (
    apply_action,
    build_city,
    parse_script_action,
    run_script,
)
from citywalk2d.input import Action
from citywalk2d.renderer import PLAYER_GLYPH


class TestBuildCity(unittest.TestCase):
    def test_builds_world_and_player(self):
        city, facades, player = build_city(width=24, height=16, seed=3)
        self.assertEqual((city.width, city.height), (24, 16))
        self.assertTrue(city.is_walkable(*player.position))
        self.assertEqual(len(facades), len(city.buildings))

    def test_player_spawns_on_first_street(self):
        city, _, player = build_city(width=24, height=16, seed=3)
        self.assertEqual(player.position, (0, 0))


class TestApplyAction(unittest.TestCase):
    def test_quit_returns_false(self):
        city, _, player = build_city(width=12, height=8, seed=3)
        self.assertFalse(apply_action(player, Action.QUIT))

    def test_movement_returns_true_and_moves(self):
        city, _, player = build_city(width=12, height=8, seed=3)
        start = player.position
        self.assertTrue(apply_action(player, Action.RIGHT))
        self.assertEqual(player.position, (start[0] + 1, start[1]))

    def test_none_is_a_noop(self):
        city, _, player = build_city(width=12, height=8, seed=3)
        start = player.position
        self.assertTrue(apply_action(player, None))
        self.assertEqual(player.position, start)


class TestScriptedWalk(unittest.TestCase):
    def test_perimeter_walk_returns_to_start(self):
        # A full lap around the city's edge: every perimeter cell is street,
        # so this walks the player all the way around without error and back
        # to (0, 0).
        city, facades, player = build_city(width=16, height=12, seed=7)
        self.assertEqual(player.position, (0, 0))
        actions = (
            [Action.RIGHT] * (city.width - 1)
            + [Action.DOWN] * (city.height - 1)
            + [Action.LEFT] * (city.width - 1)
            + [Action.UP] * (city.height - 1)
            + [Action.QUIT]
        )
        frames = []
        count = run_script(
            city, facades, player, actions,
            write_frame=frames.append, color=False,
            viewport_width=20, viewport_height=10,
        )

        self.assertEqual(player.position, (0, 0))
        self.assertEqual(count, len(actions))   # initial frame + one per step
        self.assertEqual(len(frames), count)

    def test_every_frame_is_a_wellformed_viewport(self):
        city, facades, player = build_city(width=16, height=12, seed=7)
        actions = [Action.RIGHT] * 4 + [Action.DOWN] * 3 + [Action.QUIT]
        frames = []
        run_script(
            city, facades, player, actions,
            write_frame=frames.append, color=False,
            viewport_width=20, viewport_height=10,
        )
        for frame in frames:
            lines = frame.split("\n")
            self.assertEqual(len(lines), 10)
            for line in lines:
                self.assertEqual(len(line), 20)
            self.assertIn(PLAYER_GLYPH, frame)

    def test_player_glyph_tracks_position(self):
        # With a viewport larger than the world, the whole world is centered,
        # so the player glyph's position is its world position plus the known
        # centering offset.
        city, facades, player = build_city(width=16, height=12, seed=7)
        frames = []
        run_script(
            city, facades, player, [Action.RIGHT, Action.RIGHT, Action.QUIT],
            write_frame=frames.append, color=False,
            viewport_width=40, viewport_height=20,
        )
        last = frames[-1]
        lines = last.split("\n")
        gy = next(y for y, line in enumerate(lines) if PLAYER_GLYPH in line)
        gx = lines[gy].index(PLAYER_GLYPH)
        # world 16x12 centered in viewport 40x20 -> origin (-12, -4).
        self.assertEqual((gx - 12, gy - 4), player.position)

    def test_blocked_move_does_not_error_or_move(self):
        # Walking UP off the top edge at (0, 0) is rejected; position unchanged.
        city, facades, player = build_city(width=16, height=12, seed=7)
        self.assertEqual(player.position, (0, 0))
        frames = []
        count = run_script(
            city, facades, player, [Action.UP, Action.QUIT],
            write_frame=frames.append, color=False,
            viewport_width=20, viewport_height=10,
        )
        self.assertEqual(player.position, (0, 0))
        self.assertEqual(count, 2)

    def test_exhausted_script_stops_cleanly(self):
        # No explicit QUIT: the loop should stop when the script runs out.
        city, facades, player = build_city(width=16, height=12, seed=7)
        frames = []
        count = run_script(
            city, facades, player, [Action.RIGHT],
            write_frame=frames.append, color=False,
        )
        self.assertEqual(count, 2)  # initial frame + one step
        self.assertEqual(player.position, (1, 0))


class TestParseScriptAction(unittest.TestCase):
    def test_direction_names_and_wasd(self):
        cases = {
            "up": Action.UP, "W": Action.UP,
            "down": Action.DOWN, "s": Action.DOWN,
            "left": Action.LEFT, "a": Action.LEFT,
            "right": Action.RIGHT, "D": Action.RIGHT,
            "quit": Action.QUIT, "q": Action.QUIT, "exit": Action.QUIT,
        }
        for token, expected in cases.items():
            with self.subTest(token=token):
                self.assertIs(parse_script_action(token), expected)

    def test_blank_comment_and_unknown_are_none(self):
        self.assertIsNone(parse_script_action(""))
        self.assertIsNone(parse_script_action("   "))
        self.assertIsNone(parse_script_action("# a comment"))
        self.assertIsNone(parse_script_action("jump"))


class TestEntrypointScripted(unittest.TestCase):
    def test_scripted_entrypoint_runs_without_error(self):
        script = "\n".join([
            "# walk right then down",
            "right",
            "right",
            "down",
            "quit",
            "",
        ])
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(script)
            path = f.name
        try:
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = entrypoint.main([
                    "--script", path, "--no-color",
                    "--width", "16", "--height", "12",
                    "--seed", "7", "--viewport", "20x10",
                ])
            self.assertEqual(code, 0)
            self.assertIn(PLAYER_GLYPH, out.getvalue())  # frames rendered to stdout
            self.assertIn("player at", err.getvalue())   # final-position summary
        finally:
            os.unlink(path)

    def test_interactive_requires_a_terminal(self):
        # Under a non-TTY (CI / headless), interactive mode must fail fast
        # instead of blocking on raw keyboard input.
        if sys.stdin.isatty():
            self.skipTest("running under a real terminal")
        err = io.StringIO()
        with redirect_stderr(err):
            code = entrypoint.main([])
        self.assertNotEqual(code, 0)
        self.assertIn("terminal", err.getvalue())


if __name__ == "__main__":
    unittest.main()
