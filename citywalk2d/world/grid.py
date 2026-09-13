"""City grid model for citywalk2d.

A pure-Python, stdlib-only, deterministic data layer for the 2D top-down
color-ASCII city.  The city is a coordinate grid in which every cell is
exactly one of three kinds:

* ``STREET``   -- a walkable road cell; roads form a single connected network.
* ``BUILDING`` -- a building footprint (impassable, non-overlapping).
* ``INTERIOR`` -- open ground inside a city block (not a street, not a building).

:func:`generate_city` lays down a regular grid of 1-cell-wide streets that
carve the map into city blocks, then fills each block with non-overlapping
rectangular building footprints using a seeded random number generator.  All
randomness derives from a single ``seed`` and Python's ``random`` module is
cross-platform deterministic, so the same seed always produces the same city
on Linux and Windows.

Public API consumed by downstream nodes:

* ``generate_city(...)`` -> ``CityGrid``
* ``grid.is_walkable(x, y)`` -> ``bool``
* ``grid.building_at(x, y)`` -> ``Building | None``
* ``grid.buildings`` -> tuple of ``Building`` (ascending id)
* ``grid.blocks`` -> tuple of ``Block`` (ascending id)
* ``grid.cell_type(x, y)`` -> ``CellType``
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum

__all__ = [
    "Block",
    "Building",
    "CellType",
    "CityGrid",
    "Rect",
    "generate_city",
]


class CellType(IntEnum):
    """The three mutually exclusive cell kinds in a city grid."""

    INTERIOR = 0
    STREET = 1
    BUILDING = 2


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle; ``(x, y)`` is the top-left corner, ``w`` x ``h`` size."""

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        """Exclusive right edge."""
        return self.x + self.w

    @property
    def y2(self) -> int:
        """Exclusive bottom edge."""
        return self.y + self.h

    def contains(self, x: int, y: int) -> bool:
        """True if cell ``(x, y)`` lies inside this rectangle."""
        return self.x <= x < self.x2 and self.y <= y < self.y2

    def cells(self):
        """Yield ``(x, y)`` for every cell, row-major."""
        for yy in range(self.y, self.y2):
            for xx in range(self.x, self.x2):
                yield xx, yy


@dataclass(frozen=True)
class Building:
    """A single rectangular building footprint inside a city block."""

    id: int
    rect: Rect
    block_id: int


@dataclass(frozen=True)
class Block:
    """A city block: the open interior region bounded by four streets."""

    id: int
    rect: Rect
    building_ids: tuple[int, ...]


def _rects_overlap(a: Rect, b: Rect, gap: int = 0) -> bool:
    """True if ``a`` and ``b`` overlap, each expanded by ``gap`` cells."""
    return not (
        a.x2 + gap <= b.x
        or b.x2 + gap <= a.x
        or a.y2 + gap <= b.y
        or b.y2 + gap <= a.y
    )


class CityGrid:
    """A generated city layout: streets, blocks, and building footprints."""

    def __init__(self, width: int, height: int, seed: int = 1):
        if width < 1 or height < 1:
            raise ValueError("city dimensions must be at least 1x1")
        self.width = width
        self.height = height
        self.seed = seed
        self._cells = [CellType.INTERIOR] * (width * height)
        self._buildings: dict[int, Building] = {}
        self._building_at: dict[int, int] = {}
        self._blocks: dict[int, Block] = {}

    # -- internal construction helpers (used by generate_city) ------------

    def _idx(self, x: int, y: int) -> int:
        return y * self.width + x

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _set_cell(self, x: int, y: int, kind: CellType) -> None:
        self._cells[self._idx(x, y)] = kind

    def _add_block(self, rect: Rect) -> Block:
        block = Block(id=len(self._blocks), rect=rect, building_ids=())
        self._blocks[block.id] = block
        return block

    def _add_building(self, rect: Rect, block_id: int) -> Building:
        building = Building(id=len(self._buildings), rect=rect, block_id=block_id)
        self._buildings[building.id] = building
        for x, y in rect.cells():
            self._set_cell(x, y, CellType.BUILDING)
            self._building_at[self._idx(x, y)] = building.id
        block = self._blocks[block_id]
        self._blocks[block_id] = Block(
            id=block.id,
            rect=block.rect,
            building_ids=block.building_ids + (building.id,),
        )
        return building

    # -- public read API ---------------------------------------------------

    def cell_type(self, x: int, y: int) -> CellType:
        """Return the kind of cell at ``(x, y)``; raises IndexError out of bounds."""
        if not self.in_bounds(x, y):
            raise IndexError(f"cell ({x}, {y}) is out of bounds")
        return self._cells[self._idx(x, y)]

    def is_walkable(self, x: int, y: int) -> bool:
        """True if ``(x, y)`` is a walkable street cell (False out of bounds)."""
        if not self.in_bounds(x, y):
            return False
        return self._cells[self._idx(x, y)] == CellType.STREET

    def building_at(self, x: int, y: int) -> Building | None:
        """The building whose footprint covers ``(x, y)``, or None."""
        if not self.in_bounds(x, y):
            return None
        bid = self._building_at.get(self._idx(x, y))
        return None if bid is None else self._buildings[bid]

    @property
    def buildings(self) -> tuple[Building, ...]:
        """All buildings, ascending by id."""
        return tuple(self._buildings[i] for i in range(len(self._buildings)))

    @property
    def blocks(self) -> tuple[Block, ...]:
        """All blocks, ascending by id."""
        return tuple(self._blocks[i] for i in range(len(self._blocks)))

    def block_by_id(self, block_id: int) -> Block:
        return self._blocks[block_id]

    def street_cells(self):
        """Yield ``(x, y)`` for every street cell, row-major."""
        for y in range(self.height):
            for x in range(self.width):
                if self._cells[self._idx(x, y)] == CellType.STREET:
                    yield x, y

    def render(self) -> str:
        """Return an ASCII rendering: ``#`` building, ``.`` street, space interior."""
        glyphs = {
            CellType.INTERIOR: " ",
            CellType.STREET: ".",
            CellType.BUILDING: "#",
        }
        rows = []
        for y in range(self.height):
            rows.append(
                "".join(glyphs[self._cells[self._idx(x, y)]] for x in range(self.width))
            )
        return "\n".join(rows)


def _street_axes(total: int, block_size: int) -> list[int]:
    """Street positions along one axis: 1-wide roads closing off the map edges."""
    positions = [0]
    step = block_size + 1
    while positions[-1] + step < total:
        positions.append(positions[-1] + step)
    if total > 1 and positions[-1] != total - 1:
        positions.append(total - 1)
    return positions


def _fill_block(
    grid: CityGrid,
    block: Block,
    seed: int,
    margin: int,
    building_min: int,
    building_max: int,
    buildings_per_block: tuple[int, int],
    gap: int,
) -> None:
    rect = block.rect
    x0 = rect.x + margin
    y0 = rect.y + margin
    x1 = rect.x2 - 1 - margin
    y1 = rect.y2 - 1 - margin
    buildable_w = x1 - x0 + 1
    buildable_h = y1 - y0 + 1
    if buildable_w < 1 or buildable_h < 1:
        return

    rng = random.Random(f"city:{seed}:block:{block.id}")
    lo, hi = buildings_per_block
    target = rng.randint(lo, hi)

    placed: list[Rect] = []
    attempts = max(64, target * 32)
    for _ in range(attempts):
        if len(placed) >= target:
            break
        bw = min(rng.randint(building_min, building_max), buildable_w)
        bh = min(rng.randint(building_min, building_max), buildable_h)
        x = rng.randint(x0, x1 - bw + 1)
        y = rng.randint(y0, y1 - bh + 1)
        candidate = Rect(x, y, bw, bh)
        if all(not _rects_overlap(candidate, p, gap) for p in placed):
            placed.append(candidate)
            grid._add_building(candidate, block.id)


def generate_city(
    width: int = 64,
    height: int = 44,
    seed: int = 1,
    block_width: int = 9,
    block_height: int = 7,
    margin: int = 1,
    building_min: int = 2,
    building_max: int = 5,
    buildings_per_block: tuple[int, int] = (1, 4),
    gap: int = 1,
) -> CityGrid:
    """Generate a deterministic city layout.

    A regular grid of 1-cell-wide streets splits the map into city blocks
    (roughly ``block_width`` x ``block_height`` interior cells).  Each block is
    then filled with non-overlapping rectangular building footprints, inset by
    ``margin`` cells from the surrounding streets and separated from one another
    by at least ``gap`` cells.

    The same arguments always reproduce the identical layout, on any platform
    and any Python >= 3.10.
    """
    if margin < 0 or gap < 0:
        raise ValueError("margin and gap must be >= 0")
    if building_min < 1 or building_max < building_min:
        raise ValueError("building size range is invalid")
    if block_width < 1 or block_height < 1:
        raise ValueError("block sizes must be >= 1")
    if buildings_per_block[0] < 0 or buildings_per_block[1] < buildings_per_block[0]:
        raise ValueError("buildings_per_block range is invalid")

    grid = CityGrid(width, height, seed)

    x_axes = _street_axes(width, block_width)
    y_axes = _street_axes(height, block_height)

    for x in x_axes:
        for y in range(height):
            grid._set_cell(x, y, CellType.STREET)
    for y in y_axes:
        for x in range(width):
            grid._set_cell(x, y, CellType.STREET)

    for i in range(len(x_axes) - 1):
        for j in range(len(y_axes) - 1):
            rect = Rect(
                x=x_axes[i] + 1,
                y=y_axes[j] + 1,
                w=x_axes[i + 1] - x_axes[i] - 1,
                h=y_axes[j + 1] - y_axes[j] - 1,
            )
            if rect.w < 1 or rect.h < 1:
                continue
            block = grid._add_block(rect)
            _fill_block(
                grid, block, seed, margin, building_min, building_max,
                buildings_per_block, gap,
            )

    return grid
