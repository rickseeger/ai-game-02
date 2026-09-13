"""Viewport camera for the top-down renderer.

A :class:`Camera` describes a rectangular *window* into the city: a viewport
of ``viewport_width`` x ``viewport_height`` cells whose top-left corner sits at
world cell ``(x, y)``.  It is pure data -- the math that decides *where* the
window sits (centered on the player, clamped to the map edge) lives here; the
scene renderer consumes it to decide which world cells to draw.

The camera never changes the world; it only chooses the lens.  Keeping that
decision in one small, deterministic place makes the windowing behaviour
trivially testable without touching the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Camera"]


def _clamp_origin(origin: int, viewport: int, world: int) -> int:
    """Clamp a window's top-left coordinate into the world.

    When the viewport fits inside the world, the window is clamped to
    ``[0, world - viewport]``.  When the viewport is at least as large as the
    world, the whole world is centered inside the viewport, which yields a
    (possibly negative) origin -- the caller maps world cells back through
    ``view = world - origin``, so the centering stays consistent.
    """
    if viewport >= world:
        return -(viewport - world) // 2
    return max(0, min(origin, world - viewport))


@dataclass(frozen=True)
class Camera:
    """A viewport window into a world: top-left at ``(x, y)``, ``viewport`` wide."""

    viewport_width: int
    viewport_height: int
    world_width: int
    world_height: int
    x: int
    y: int

    def __post_init__(self) -> None:
        if self.viewport_width < 1 or self.viewport_height < 1:
            raise ValueError("viewport dimensions must be >= 1")
        if self.world_width < 1 or self.world_height < 1:
            raise ValueError("world dimensions must be >= 1")

    @classmethod
    def centered_on(
        cls,
        cx: int,
        cy: int,
        viewport_width: int,
        viewport_height: int,
        world_width: int,
        world_height: int,
    ) -> "Camera":
        """Return a camera whose viewport is centered on world cell ``(cx, cy)``.

        Centering is best-effort: near the map edge the window is clamped so it
        never shows space past the world.  ``cx``/``cy`` need not lie inside the
        world (the clamp still yields a valid window).
        """
        x = _clamp_origin(cx - viewport_width // 2, viewport_width, world_width)
        y = _clamp_origin(cy - viewport_height // 2, viewport_height, world_height)
        return cls(viewport_width, viewport_height, world_width, world_height, x, y)

    @property
    def window(self) -> tuple[int, int, int, int]:
        """The world-space viewport as ``(x0, y0, x1, y1)`` (exclusive edges)."""
        return (self.x, self.y, self.x + self.viewport_width, self.y + self.viewport_height)

    def world_to_view(self, wx: int, wy: int) -> tuple[int, int]:
        """Map a world cell to its viewport coordinate (may be out of range)."""
        return (wx - self.x, wy - self.y)

    def view_to_world(self, vx: int, vy: int) -> tuple[int, int]:
        """Map a viewport coordinate back to its world cell."""
        return (vx + self.x, vy + self.y)

    def contains_world(self, wx: int, wy: int) -> bool:
        """True if world cell ``(wx, wy)`` falls inside the viewport."""
        vx, vy = self.world_to_view(wx, wy)
        return 0 <= vx < self.viewport_width and 0 <= vy < self.viewport_height

    def centers(self, cx: int, cy: int) -> bool:
        """True if ``(cx, cy)`` lands on the viewport's center cell."""
        vx, vy = self.world_to_view(cx, cy)
        return vx == self.viewport_width // 2 and vy == self.viewport_height // 2
