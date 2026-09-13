"""Player entity and one-cell movement for citywalk2d.

A pure-Python, stdlib-only gameplay data layer that sits on top of the city
grid (:mod:`citywalk2d.world.grid`).  The player is a point standing on a
single street cell; :meth:`Player.move` advances it one cell at a time and
never into a building, a block interior, or out of bounds.

Movement is deliberately *logical*: it consumes a canonical
:class:`Direction` (UP / DOWN / LEFT / RIGHT) and mutates the player's
``(x, y)`` position.  Raw keyboard decoding is *not* this module's job --
the input node maps WASD / arrow keys onto :class:`Direction` and then calls
``player.move``.  This keeps movement pure, deterministic, and trivially
testable with no terminal I/O.

Public API consumed by downstream nodes:

* ``spawn_player(city, seed=None)`` -> ``Player`` standing on a street cell
* ``Player.move(direction)`` -> ``bool`` (True if the step was taken)
* ``Player.position`` -> ``(x, y)``
* ``Direction`` -- UP / DOWN / LEFT / RIGHT, each carrying a unit ``delta``
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .grid import CityGrid

__all__ = [
    "Direction",
    "Player",
    "spawn_player",
]


class Direction(Enum):
    """The four canonical movement directions, each carrying a unit delta."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    def __init__(self, dx: int, dy: int) -> None:
        self.dx = dx
        self.dy = dy

    @property
    def delta(self) -> tuple[int, int]:
        """The ``(dx, dy)`` offset applied when moving this direction."""
        return (self.dx, self.dy)


@dataclass
class Player:
    """A player standing on a street cell, able to move one cell per step."""

    grid: CityGrid
    x: int
    y: int

    def __post_init__(self) -> None:
        if not self.grid.is_walkable(self.x, self.y):
            raise ValueError(
                f"player spawn ({self.x}, {self.y}) is not a walkable street cell"
            )

    @property
    def position(self) -> tuple[int, int]:
        """The player's current ``(x, y)`` cell."""
        return (self.x, self.y)

    def move(self, direction: Direction) -> bool:
        """Attempt to move exactly one cell in ``direction``.

        The step succeeds only when the target cell is a walkable street cell,
        which implies it is inside the grid bounds and is neither a building
        nor a block interior.  On success the player advances exactly one cell
        and ``True`` is returned; otherwise the position is unchanged and
        ``False`` is returned (the move is rejected).
        """
        nx = self.x + direction.dx
        ny = self.y + direction.dy
        if not self.grid.is_walkable(nx, ny):
            return False
        self.x = nx
        self.y = ny
        return True


def spawn_player(grid: CityGrid, seed: int | None = None) -> Player:
    """Place a new player on a guaranteed street cell.

    The spawn cell is deterministic: the first street cell in row-major order
    when ``seed`` is ``None``, otherwise a seeded random pick among all street
    cells.  Raises ``ValueError`` if the city has no street cells at all.
    """
    streets = list(grid.street_cells())
    if not streets:
        raise ValueError("city has no walkable street cells to spawn on")
    if seed is None:
        x, y = streets[0]
    else:
        rng = random.Random(f"citywalk2d:player:{seed}")
        x, y = rng.choice(streets)
    return Player(grid, x, y)
