"""Frame buffer for the top-down color-ASCII renderer.

The frame buffer is the renderer's single source of truth for *what* a frame
looks like: a 2-D grid of :class:`Cell` values, each holding exactly one
character plus an optional ANSI 256-color foreground and background.  It is
pure data -- no terminal I/O, no platform branches, no randomness -- so every
mapping from a city cell to a ``(char, fg, bg)`` triple is deterministic and
unit-testable headlessly.

Color is expressed as ANSI 256-color palette indices (integers ``0..255``),
serialised to SGR escape sequences with :func:`sgr`.  ``None`` means "no
colour / terminal default".

Public API consumed by downstream nodes:

* ``Cell(char, fg=None, bg=None)`` -- one character + optional colors
* ``FrameBuffer(width, height)`` -- a grid of cells
* ``fb.set(x, y, cell)`` / ``fb.get(x, y)`` -- read/write one cell
* ``fb.render(color=True)`` -- serialize the whole buffer to a string
* ``sgr(fg=None, bg=None)`` -- build an ANSI 256-color SGR sequence
* ``strip_ansi(text)`` -- remove ANSI sequences (handy in tests)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "ANSI_ESCAPE_RE",
    "Cell",
    "FrameBuffer",
    "RESET",
    "sgr",
    "strip_ansi",
]

#: ANSI SGR reset: restores default foreground and background.
RESET = "\x1b[0m"

#: Matches the SGR sequences this renderer emits (used by :func:`strip_ansi`).
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _check_color(value: int) -> None:
    """Raise unless ``value`` is an ANSI 256-color palette index (0..255)."""
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 255:
        raise ValueError(f"color index must be an int in 0..255, got {value!r}")


def sgr(fg: int | None = None, bg: int | None = None) -> str:
    """Build an ANSI 256-color SGR sequence (``''`` when both colors are None).

    Foreground uses ``38;5;N`` and background uses ``48;5;N``; both may be
    combined into one sequence.  Returns an empty string when no color is set.
    """
    parts: list[str] = []
    if fg is not None:
        _check_color(fg)
        parts.append(f"38;5;{fg}")
    if bg is not None:
        _check_color(bg)
        parts.append(f"48;5;{bg}")
    if not parts:
        return ""
    return "\x1b[" + ";".join(parts) + "m"


def strip_ansi(text: str) -> str:
    """Return ``text`` with every SGR sequence removed."""
    return ANSI_ESCAPE_RE.sub("", text)


@dataclass(frozen=True)
class Cell:
    """A single frame-buffer cell: one character plus optional ANSI colors.

    ``fg`` and ``bg`` are ANSI 256-color palette indices (``0..255``) or
    ``None`` for the terminal default.  Cells are immutable so a shared
    default cell can safely fill an entire buffer.
    """

    char: str = " "
    fg: int | None = None
    bg: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.char, str) or len(self.char) != 1:
            raise ValueError(f"Cell.char must be a single character, got {self.char!r}")
        if self.fg is not None:
            _check_color(self.fg)
        if self.bg is not None:
            _check_color(self.bg)


class FrameBuffer:
    """A 2-D grid of :class:`Cell` values of fixed ``width`` x ``height``.

    Every cell starts as ``default`` (an empty, uncolored cell unless told
    otherwise).  Out-of-bounds access raises ``IndexError`` -- callers doing
    viewport math that can overrun the world are expected to check bounds
    first (the scene renderer does exactly that).
    """

    def __init__(self, width: int, height: int, default: Cell | None = None) -> None:
        if not isinstance(width, int) or width < 1:
            raise ValueError("FrameBuffer width must be a positive int")
        if not isinstance(height, int) or height < 1:
            raise ValueError("FrameBuffer height must be a positive int")
        if default is None:
            default = Cell()
        if not isinstance(default, Cell):
            raise TypeError("default must be a Cell")
        self.width = width
        self.height = height
        # Cell is immutable, so sharing one default instance is safe.
        self._cells: list[list[Cell]] = [[default] * width for _ in range(height)]

    def _check_bounds(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"cell ({x}, {y}) out of bounds for {self.width}x{self.height} buffer"
            )

    def set(self, x: int, y: int, cell: Cell) -> None:
        """Write ``cell`` at ``(x, y)`` (raises ``IndexError`` out of bounds)."""
        self._check_bounds(x, y)
        if not isinstance(cell, Cell):
            raise TypeError("cell must be a Cell")
        self._cells[y][x] = cell

    def get(self, x: int, y: int) -> Cell:
        """Return the cell at ``(x, y)`` (raises ``IndexError`` out of bounds)."""
        self._check_bounds(x, y)
        return self._cells[y][x]

    @property
    def rows(self) -> list[list[Cell]]:
        """A copy of the buffer as ``height`` rows of ``width`` cells."""
        return [list(row) for row in self._cells]

    def render(self, color: bool = True) -> str:
        """Serialize the buffer to a string of ``height`` newline-joined rows.

        With ``color=True`` each cell is emitted with the minimum number of
        ANSI sequences: an SGR sequence is written only when the foreground or
        background changes, and a reset is written at the end of every row so
        colours never bleed across a line boundary.  With ``color=False`` only
        the characters are emitted (no escapes), which is useful for eyeballing
        geometry and for tests.
        """
        lines: list[str] = []
        for row in self._cells:
            parts: list[str] = []
            cur_fg: int | None = None
            cur_bg: int | None = None
            for cell in row:
                if color and (cell.fg != cur_fg or cell.bg != cur_bg):
                    code = sgr(cell.fg, cell.bg)
                    if code:
                        parts.append(code)
                    elif cur_fg is not None or cur_bg is not None:
                        parts.append(RESET)
                    cur_fg, cur_bg = cell.fg, cell.bg
                parts.append(cell.char)
            if color and (cur_fg is not None or cur_bg is not None):
                parts.append(RESET)
            lines.append("".join(parts))
        return "\n".join(lines)
