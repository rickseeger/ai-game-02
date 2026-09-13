"""Cross-platform terminal keyboard input for citywalk2d.

Reads WASD and arrow keys from a terminal and maps raw byte / escape
sequences onto a canonical :class:`Action` enum whose four movement members
(UP / DOWN / LEFT / RIGHT) carry the matching
:class:`citywalk2d.world.player.Direction`.

The module is deliberately split into two layers:

* The **mapping layer** is pure and deterministic.  A keypress is just a
  short byte sequence, and :func:`map_bytes` turns one *complete* sequence
  into an :class:`Action` (or ``None`` for anything unrecognised).  This
  layer is fully unit-testable with no terminal at all -- the same bytes
  decode to the same action on every platform.

* The **platform layer** is :class:`KeyReader`.  On POSIX it drops the
  terminal into cbreak mode (no line buffering, no echo, Ctrl-C still
  works) and reads bytes directly from the tty; on Windows it reads
  virtual-key sequences through ``msvcrt.getwch``.  Both feed the raw
  sequence through :func:`map_bytes` and hand back the same ``Action``
  values.  This layer needs a real terminal and is exercised interactively
  (which is why the completion contract confirms live keys on a laptop
  rather than headless).

Public API consumed by downstream nodes:

* ``Action`` -- canonical actions; ``action.direction`` is the ``Direction``
* ``map_bytes(seq)`` -> ``Action | None`` (pure, deterministic)
* ``KeyReader`` -- blocking single-keypress reader (POSIX + Windows)
* ``iter_actions(reader)`` -> iterator of ``Action``, stops after ``QUIT``
* ``self_test()`` -> ``bool`` (runs the deterministic mapping checks)

Example::

    from citywalk2d.input import Action, KeyReader

    with KeyReader() as keys:
        action = keys.read()          # blocks for one keypress
        if action is Action.QUIT:
            ...                        # stop the loop
        elif action is not None:
            player.move(action.direction)
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Iterator

from ..world import Direction

__all__ = [
    "Action",
    "KEYMAP",
    "KeyReader",
    "iter_actions",
    "map_bytes",
    "self_test",
]


class Action(Enum):
    """Canonical player actions decoded from raw terminal key input.

    The four movement members mirror :class:`Direction` exactly: each member's
    enum *value* is the matching ``Direction``, so ``action.direction`` is
    ``Direction.UP`` / ``DOWN`` / ``LEFT`` / ``RIGHT``.  ``QUIT`` carries no
    direction (its value is ``None``) and signals the game loop to exit.
    """

    UP = Direction.UP
    DOWN = Direction.DOWN
    LEFT = Direction.LEFT
    RIGHT = Direction.RIGHT
    QUIT = None

    @property
    def direction(self) -> "Direction | None":
        """The movement :class:`Direction` this action drives (``None`` for QUIT)."""
        return self.value

    @property
    def is_movement(self) -> bool:
        """True for the four movement actions, False for QUIT."""
        return self is not Action.QUIT


#: Every recognised single-keypress byte sequence -> its canonical Action.
#: Deterministic and platform-agnostic: the *same* bytes mean the *same*
#: action whether they were produced by a POSIX terminal or a Windows console.
KEYMAP: dict[bytes, Action] = {
    # --- WASD (plus their shifted forms) ---
    b"w": Action.UP,
    b"W": Action.UP,
    b"s": Action.DOWN,
    b"S": Action.DOWN,
    b"a": Action.LEFT,
    b"A": Action.LEFT,
    b"d": Action.RIGHT,
    b"D": Action.RIGHT,
    # --- quit keys ---
    b"q": Action.QUIT,
    b"Q": Action.QUIT,
    b"\x03": Action.QUIT,   # Ctrl-C (fires only when ISIG is disabled)
    b"\x1b": Action.QUIT,   # lone Escape
    # --- Linux/macOS ANSI/VT100 arrow-key escape sequences ---
    b"\x1b[A": Action.UP,
    b"\x1b[B": Action.DOWN,
    b"\x1b[C": Action.RIGHT,
    b"\x1b[D": Action.LEFT,
    # --- Windows console virtual-key sequences (msvcrt.getwch) ---
    # Special keys come back as a two-char pair: a \x00 or \xe0 lead byte
    # followed by a scan code.  Arrows are H (up), P (down), K (left), M
    # (right).  Both lead bytes are accepted for robustness.
    b"\xe0H": Action.UP,
    b"\xe0P": Action.DOWN,
    b"\xe0K": Action.LEFT,
    b"\xe0M": Action.RIGHT,
    b"\x00H": Action.UP,
    b"\x00P": Action.DOWN,
    b"\x00K": Action.LEFT,
    b"\x00M": Action.RIGHT,
}


def map_bytes(seq: bytes) -> "Action | None":
    """Map one complete key byte-sequence to an ``Action`` (``None`` if unknown).

    Pure and deterministic: no terminal access, no randomness, no platform
    branches.  ``seq`` must be a ``bytes`` (or ``bytearray``) holding the full
    sequence for a single keypress -- e.g. ``b"w"``, ``b"\\x1b[A"``, or the
    Windows pair ``b"\\xe0H"``.
    """
    return KEYMAP.get(bytes(seq))


class KeyReader:
    """Blocking single-keypress reader for POSIX and Windows terminals.

    On POSIX it switches the terminal into cbreak mode for the lifetime of the
    reader and restores the original mode on exit; on Windows it reads
    virtual-key sequences with ``msvcrt.getwch``.  In both cases :meth:`read`
    returns the decoded :class:`Action` (or ``None`` for an unrecognised key).
    Prefer the context-manager form so the terminal is always restored::

        with KeyReader() as keys:
            action = keys.read()
            if action is Action.QUIT:
                ...
            elif action is not None:
                player.move(action.direction)
    """

    def __init__(self, stream=None) -> None:
        # ``stream`` exists mainly for testability on POSIX; it defaults to
        # the process's standard input.
        self._stream = stream if stream is not None else sys.stdin
        self._fd = None
        self._saved = None
        self._is_windows = os.name == "nt"

    # -- context management (raw/cbreak mode on POSIX) ---------------------

    def __enter__(self) -> "KeyReader":
        if not self._is_windows:
            import termios
            import tty

            self._fd = self._stream.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._fd is not None and self._saved is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            self._fd = None
            self._saved = None
        return False

    # -- reading -----------------------------------------------------------

    def read(self) -> "Action | None":
        """Read one keypress and return its ``Action`` (``None`` if unknown)."""
        seq = self._read_windows() if self._is_windows else self._read_posix()
        return map_bytes(seq)

    def _read_posix(self) -> bytes:
        first = os.read(self._fd, 1)
        if first == b"\x1b":
            # An escape sequence (arrow key) may follow; drain whatever the
            # terminal has already queued without blocking on the user again.
            first += self._drain_available()
        return first

    def _drain_available(self) -> bytes:
        import select

        buf = bytearray()
        timeout = 0.05  # ample time for a terminal to deliver a full arrow seq
        while len(buf) < 2:  # arrows are ESC + exactly 2 more bytes
            ready, _, _ = select.select([self._fd], [], [], timeout)
            if not ready:
                break
            chunk = os.read(self._fd, 1)
            if not chunk:
                break
            buf += chunk
            timeout = 0.0  # already-queued bytes should be there immediately
        return bytes(buf)

    def _read_windows(self) -> bytes:
        import msvcrt

        first = msvcrt.getwch()
        if first in ("\x00", "\xe0"):
            second = msvcrt.getwch()
            # Latin-1 keeps the \x00 / \xe0 lead byte intact (UTF-8 would
            # expand \xe0 into two bytes and break the KEYMAP match).
            return (first + second).encode("latin-1")
        return first.encode("latin-1")


def iter_actions(reader: "KeyReader | None" = None) -> Iterator[Action]:
    """Yield each decoded ``Action``; stop cleanly after ``QUIT`` (inclusive).

    Convenience for a game loop::

        for action in iter_actions():
            if action.is_movement:
                player.move(action.direction)
            elif action is Action.QUIT:
                break

    The reader's raw mode is entered and restored automatically.
    """
    if reader is None:
        reader = KeyReader()
    with reader:
        while True:
            action = reader.read()
            if action is None:
                continue  # unrecognised key -- skip silently
            yield action
            if action is Action.QUIT:
                break


def self_test() -> bool:
    """Run the deterministic key-mapping checks headlessly.

    Mirrors the assertions in ``tests/test_input.py`` so the module can be
    self-verified directly::

        python3 -m citywalk2d.input

    Returns ``True`` when every check passes and raises ``AssertionError``
    (with a message naming the failing sequence) otherwise.
    """
    cases = [
        # WASD
        (b"w", Action.UP), (b"W", Action.UP),
        (b"s", Action.DOWN), (b"S", Action.DOWN),
        (b"a", Action.LEFT), (b"A", Action.LEFT),
        (b"d", Action.RIGHT), (b"D", Action.RIGHT),
        # arrows -- Linux/macOS ANSI escape sequences
        (b"\x1b[A", Action.UP), (b"\x1b[B", Action.DOWN),
        (b"\x1b[C", Action.RIGHT), (b"\x1b[D", Action.LEFT),
        # arrows -- Windows virtual-key sequences (\xe0 and \x00 lead bytes)
        (b"\xe0H", Action.UP), (b"\xe0P", Action.DOWN),
        (b"\xe0K", Action.LEFT), (b"\xe0M", Action.RIGHT),
        (b"\x00H", Action.UP), (b"\x00P", Action.DOWN),
        (b"\x00K", Action.LEFT), (b"\x00M", Action.RIGHT),
        # quit
        (b"q", Action.QUIT), (b"Q", Action.QUIT),
        (b"\x03", Action.QUIT), (b"\x1b", Action.QUIT),
    ]
    for seq, expected in cases:
        got = map_bytes(seq)
        assert got is expected, f"{seq!r}: expected {expected}, got {got}"

    # Every movement action carries the matching Direction; QUIT carries none.
    direction_by_action = {
        Action.UP: Direction.UP,
        Action.DOWN: Direction.DOWN,
        Action.LEFT: Direction.LEFT,
        Action.RIGHT: Direction.RIGHT,
        Action.QUIT: None,
    }
    for action, direction in direction_by_action.items():
        assert action.direction is direction, f"{action}: wrong direction"
        assert action.is_movement is (direction is not None), \
            f"{action}: is_movement mismatch"

    # Unrecognised sequences must map to None, never to an accidental action.
    for unknown in (b"", b"x", b"1", b"\x7f", b"\x1b[E", b"\xe0X", b"\x00Z"):
        assert map_bytes(unknown) is None, f"{unknown!r} should be unknown"

    return True
