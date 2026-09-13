"""Unit tests for the cross-platform keyboard-input module (node G10/5).

Covers the deterministic mapping layer in :mod:`citywalk2d.input`:

1. WASD letters (lowercase and shifted) map to the matching movement Action.
2. Linux/macOS ANSI arrow-key escape sequences map correctly.
3. Windows console virtual-key sequences (\\xe0 / \\x00 lead bytes) map correctly.
4. Quit keys (q / Q / Ctrl-C / Escape) map to Action.QUIT.
5. Every movement Action carries the matching player Direction; QUIT does not.
6. Unknown byte sequences map to None (never to an accidental action).

Raw terminal reading (termios / msvcrt) is intentionally not exercised here --
it needs a real keyboard and is confirmed live on a laptop per the completion
contract.  Only the pure, deterministic mapping is testable headless.
"""

import unittest

from citywalk2d.input import Action, KEYMAP, map_bytes
from citywalk2d.world import Direction

# (sequence, expected action) for every byte/escape sequence we must decode.
CASES = [
    # WASD (lowercase + shifted)
    (b"w", Action.UP), (b"W", Action.UP),
    (b"s", Action.DOWN), (b"S", Action.DOWN),
    (b"a", Action.LEFT), (b"A", Action.LEFT),
    (b"d", Action.RIGHT), (b"D", Action.RIGHT),
    # Linux/macOS ANSI arrow-key escape sequences
    (b"\x1b[A", Action.UP),
    (b"\x1b[B", Action.DOWN),
    (b"\x1b[C", Action.RIGHT),
    (b"\x1b[D", Action.LEFT),
    # Windows console virtual-key sequences (\xe0 lead byte)
    (b"\xe0H", Action.UP),
    (b"\xe0P", Action.DOWN),
    (b"\xe0K", Action.LEFT),
    (b"\xe0M", Action.RIGHT),
    # Windows console virtual-key sequences (\x00 lead byte, older consoles)
    (b"\x00H", Action.UP),
    (b"\x00P", Action.DOWN),
    (b"\x00K", Action.LEFT),
    (b"\x00M", Action.RIGHT),
    # quit keys
    (b"q", Action.QUIT),
    (b"Q", Action.QUIT),
    (b"\x03", Action.QUIT),   # Ctrl-C
    (b"\x1b", Action.QUIT),   # lone Escape
]


class TestMapping(unittest.TestCase):
    def test_every_sequence_maps_to_expected_action(self):
        for seq, expected in CASES:
            with self.subTest(seq=seq):
                self.assertIs(map_bytes(seq), expected, seq)

    def test_mapping_is_deterministic(self):
        for seq, expected in CASES:
            with self.subTest(seq=seq):
                self.assertIs(map_bytes(seq), map_bytes(seq))
                self.assertIs(map_bytes(bytes(seq)), expected)

    def test_movement_actions_carry_matching_direction(self):
        expected = {
            Action.UP: Direction.UP,
            Action.DOWN: Direction.DOWN,
            Action.LEFT: Direction.LEFT,
            Action.RIGHT: Direction.RIGHT,
            Action.QUIT: None,
        }
        for action, direction in expected.items():
            with self.subTest(action=action):
                self.assertIs(action.direction, direction)
                self.assertIs(action.is_movement, direction is not None)

    def test_movement_actions_are_exactly_the_four_directions(self):
        movement = {a for a in Action if a.is_movement}
        self.assertEqual(
            movement,
            {Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT},
        )
        # One canonical action per direction, and nothing else.
        self.assertEqual(
            {a.direction for a in movement},
            {Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT},
        )

    def test_unknown_sequences_map_to_none(self):
        for unknown in (b"", b"x", b"1", b"\x7f", b"\x1b[E", b"\xe0X", b"\x00Z"):
            with self.subTest(seq=unknown):
                self.assertIsNone(map_bytes(unknown), unknown)


class TestKeymapShape(unittest.TestCase):
    def test_keys_are_bytes_values_are_actions(self):
        self.assertTrue(KEYMAP)
        for seq, action in KEYMAP.items():
            self.assertIsInstance(seq, bytes)
            self.assertIsInstance(action, Action)

    def test_no_duplicate_sequences(self):
        # A dict cannot hold duplicate keys, so this is really checking that
        # the table was not accidentally defined with collisions elsewhere.
        self.assertEqual(len(KEYMAP), len(set(KEYMAP)))

    def test_all_actions_are_reachable_from_the_table(self):
        reachable = set(KEYMAP.values())
        for action in Action:
            self.assertIn(action, reachable)


if __name__ == "__main__":
    unittest.main()
