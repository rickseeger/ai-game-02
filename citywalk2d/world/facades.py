"""Building facades for citywalk2d.

A pure-Python, stdlib-only, deterministic data layer that sits on top of the
city grid (:mod:`citywalk2d.world.grid`) and gives every building a colorful
ASCII facade.

A *facade* is pure data: a named ASCII *pattern* (a small tile of characters
that repeats to fill any rectangle) plus an ANSI *color scheme* (foreground
and background color codes).  No terminal I/O happens here -- raw mode and
Windows ANSI enabling belong to the renderer node, not this module.  This
layer only decides *what* each building looks like and produces the strings
that back that decision.

Assignment is seeded: :func:`assign_facades` derives all of its randomness
from a single seed (defaulting to the city's own seed), so the same seed
always produces the same city of facades on Linux and Windows.  Assignment
also avoids immediate repeats, so consecutive buildings (which follow block
order) never share a pattern or a color scheme -- variety is spread across
the city instead of clustering on one style.

Public API consumed by downstream nodes:

* ``assign_facades(city, seed=None)`` -> ``FacadeMap``
* ``facades.facade_for(building_id)`` -> ``Facade``
* ``facade.render(width, height)`` -> ``list[str]`` (height rows of width chars)
* ``facade.scheme`` -> ``ColorScheme`` (``.fg`` / ``.bg`` ANSI codes)
* ``render_colored_city(city, facades)`` -> a colored ASCII rendering
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .grid import CellType, CityGrid

__all__ = [
    "ColorScheme",
    "Facade",
    "FacadeMap",
    "PATTERNS",
    "RESET",
    "SCHEMES",
    "assign_facades",
    "render_colored_city",
    "wrap_color",
]

# -- ANSI color helpers ---------------------------------------------------

RESET = "\x1b[0m"

# Standard 16-color ANSI SGR codes (foreground and background).
_FOREGROUND = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

_BACKGROUND = {
    "black": "40",
    "red": "41",
    "green": "42",
    "yellow": "43",
    "blue": "44",
    "magenta": "45",
    "cyan": "46",
    "white": "47",
    "bright_black": "100",
    "bright_red": "101",
    "bright_green": "102",
    "bright_yellow": "103",
    "bright_blue": "104",
    "bright_magenta": "105",
    "bright_cyan": "106",
    "bright_white": "107",
}


def _sgr(fg: str | None = None, bg: str | None = None) -> str:
    """Build an SGR escape sequence from raw color codes ('' when colorless)."""
    parts = [p for p in (fg, bg) if p]
    if not parts:
        return ""
    return "\x1b[" + ";".join(parts) + "m"


def wrap_color(text: str, fg: str | None = None, bg: str | None = None) -> str:
    """Wrap ``text`` in an ANSI color sequence (returns it unchanged if colorless)."""
    code = _sgr(fg, bg)
    if not code:
        return text
    return code + text + RESET


@dataclass(frozen=True)
class ColorScheme:
    """A named pair of ANSI foreground/background color codes."""

    name: str
    fg: str
    bg: str

    def wrap(self, text: str) -> str:
        """Return ``text`` wrapped in this scheme's color sequence."""
        return wrap_color(text, self.fg, self.bg)


# -- palette: color schemes ----------------------------------------------

SCHEMES: tuple[ColorScheme, ...] = (
    ColorScheme("brick_red", _FOREGROUND["bright_white"], _BACKGROUND["red"]),
    ColorScheme("ocean", _FOREGROUND["black"], _BACKGROUND["cyan"]),
    ColorScheme("sunshine", _FOREGROUND["black"], _BACKGROUND["yellow"]),
    ColorScheme("forest", _FOREGROUND["bright_white"], _BACKGROUND["green"]),
    ColorScheme("royal", _FOREGROUND["bright_white"], _BACKGROUND["blue"]),
    ColorScheme("grape", _FOREGROUND["bright_white"], _BACKGROUND["magenta"]),
    ColorScheme("graphite", _FOREGROUND["bright_white"], _BACKGROUND["bright_black"]),
    ColorScheme("porcelain", _FOREGROUND["black"], _BACKGROUND["bright_white"]),
)

# -- palette: ASCII patterns ---------------------------------------------

# Each pattern is a small tile of equal-width rows that repeats to fill any
# building footprint.  Plain ASCII only, so it renders on every platform.
PATTERNS: dict[str, tuple[str, ...]] = {
    "brick": (
        "#.#.#.",
        ".#.#.#",
        "#.#.#.",
    ),
    "window": (
        "+--+",
        "|  |",
        "+--+",
    ),
    "door": (
        "+--+",
        "|oo|",
        "|##|",
    ),
    "awning": (
        "|#|#",
        "|#|#",
        "====",
    ),
    "tile": (
        "##..",
        "##..",
        "..##",
    ),
    "rooftop": (
        "^^^^",
        "^^^^",
        "^^^^",
    ),
    "stone": (
        "oOoO",
        "OoOo",
        "oOoO",
    ),
    "mosaic": (
        "~%~%",
        "%~%~",
        "~%~%",
    ),
}


def _validate_patterns() -> None:
    """Fail fast at import if any pattern tile is malformed."""
    for name, tile in PATTERNS.items():
        if not tile:
            raise ValueError(f"facade pattern {name!r} has no rows")
        width = len(tile[0])
        if width < 1:
            raise ValueError(f"facade pattern {name!r} has zero-width rows")
        for row in tile:
            if len(row) != width:
                raise ValueError(f"facade pattern {name!r} rows have unequal widths")


_validate_patterns()


@dataclass(frozen=True)
class Facade:
    """A single building's look: a named pattern plus a color scheme."""

    name: str
    scheme: ColorScheme
    pattern: tuple[str, ...]

    @property
    def fg(self) -> str:
        return self.scheme.fg

    @property
    def bg(self) -> str:
        return self.scheme.bg

    def render(self, width: int, height: int) -> list[str]:
        """Tile the pattern into exactly ``width`` x ``height`` rows of text.

        The result is ``height`` strings, each ``width`` characters long,
        holding the repeated pattern (no ANSI codes -- color is applied by the
        caller via :attr:`scheme`).  Works for any width/height >= 1.
        """
        if width < 1 or height < 1:
            raise ValueError("facade render dimensions must be >= 1")
        tile = self.pattern
        tile_h = len(tile)
        tile_w = len(tile[0])
        rows = []
        for y in range(height):
            row = tile[y % tile_h]
            rows.append("".join(row[x % tile_w] for x in range(width)))
        return rows


class FacadeMap:
    """The facade assigned to every building of a city, keyed by building id."""

    def __init__(self, seed: int, facades_by_id: dict[int, Facade]):
        self.seed = seed
        self._facades = dict(facades_by_id)

    def facade_for(self, building_id: int) -> Facade:
        """The facade for the given building id (raises KeyError if unknown)."""
        return self._facades[building_id]

    def __len__(self) -> int:
        return len(self._facades)

    @property
    def facades(self) -> tuple[Facade, ...]:
        """All facades in ascending building-id order."""
        return tuple(self._facades[i] for i in sorted(self._facades))


def assign_facades(city: CityGrid, seed: int | None = None) -> FacadeMap:
    """Assign a varied, colorful facade to every building in ``city``.

    The assignment is deterministic in ``seed`` (defaulting to ``city.seed``)
    and avoids immediate repeats so no two consecutive buildings share a
    pattern or a color scheme.
    """
    if seed is None:
        seed = city.seed
    rng = random.Random(f"citywalk2d:facades:{seed}")

    pattern_names = list(PATTERNS)
    rng.shuffle(pattern_names)
    scheme_list = list(SCHEMES)
    rng.shuffle(scheme_list)

    def _pick(items, previous):
        """Pick an item, never repeating the previous one (when possible)."""
        if len(items) == 1:
            return items[0]
        choices = [it for it in items if it != previous]
        return rng.choice(choices)

    facades: dict[int, Facade] = {}
    prev_pattern = None
    prev_scheme = None
    for building in city.buildings:
        pname = _pick(pattern_names, prev_pattern)
        scheme = _pick(scheme_list, prev_scheme)
        facades[building.id] = Facade(pname, scheme, PATTERNS[pname])
        prev_pattern, prev_scheme = pname, scheme

    return FacadeMap(seed, facades)


def render_colored_city(city: CityGrid, facades: FacadeMap) -> str:
    """Return a colorized ASCII rendering of the whole city.

    Streets are ``.`` and block interiors are spaces (uncolored); each
    building cell is drawn with its facade's pattern glyph wrapped in that
    building's ANSI color scheme.  Pure data composition -- no terminal
    I/O -- useful for eyeballing variety and for the renderer to build on.
    """
    glyphs = {
        CellType.INTERIOR: " ",
        CellType.STREET: ".",
    }
    rows = []
    for y in range(city.height):
        line = []
        for x in range(city.width):
            kind = city.cell_type(x, y)
            if kind == CellType.BUILDING:
                building = city.building_at(x, y)
                facade = facades.facade_for(building.id)
                tile = facade.pattern
                lx = x - building.rect.x
                ly = y - building.rect.y
                glyph = tile[ly % len(tile)][lx % len(tile[0])]
                line.append(facade.scheme.wrap(glyph))
            else:
                line.append(glyphs[kind])
        rows.append("".join(line))
    return "\n".join(rows)
