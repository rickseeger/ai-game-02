"""Scene renderer: turn a city + facades + player into a colored top-down frame.

This is where the world's three layers (grid, facades, player) are composed
into a picture.  :func:`render_frame` walks the camera's viewport and, for
every world cell inside it, writes a :class:`~citywalk2d.renderer.framebuffer.Cell`
into a frame buffer:

* ``STREET``   -> painted asphalt (a space with a dark-gray background)
* ``INTERIOR`` -> painted concrete (a space with a slightly lighter background)
* ``BUILDING`` -> the facade's pattern glyph, colored with the facade's scheme
* the player   -> ``@`` on a bright highlight, drawn last on top of the street

The facade layer (``citywalk2d.world.facades``) expresses color as 16-color
ANSI SGR strings; :func:`scheme_to_256` maps those onto the equivalent
256-color palette indices so the whole frame uses one consistent color model.

Public API consumed by downstream nodes:

* ``render(city, facades, player, ...)`` -> colored frame string
* ``render_frame(city, facades, player, ...)`` -> ``FrameBuffer``
* ``scheme_to_256(scheme)`` -> ``(fg, bg)`` 256-color indices
"""

from __future__ import annotations

from ..world import CellType
from .camera import Camera
from .framebuffer import Cell, FrameBuffer

__all__ = [
    "DEFAULT_VIEWPORT_HEIGHT",
    "DEFAULT_VIEWPORT_WIDTH",
    "INTERIOR_BG",
    "INTERIOR_GLYPH",
    "PLAYER_BG",
    "PLAYER_FG",
    "PLAYER_GLYPH",
    "STREET_BG",
    "STREET_GLYPH",
    "render",
    "render_frame",
    "scheme_to_256",
]

# -- display palette (ANSI 256-color indices) -----------------------------

#: Default viewport size when the caller does not provide a camera or size.
DEFAULT_VIEWPORT_WIDTH = 80
DEFAULT_VIEWPORT_HEIGHT = 24

#: Player marker: ``@`` in black on a bright-yellow highlight.
PLAYER_GLYPH = "@"
PLAYER_FG = 16   # black
PLAYER_BG = 226  # bright yellow

#: Streets read as dark asphalt; block interiors read as slightly lighter
#: concrete so the two stay visually distinct even when adjacent.
STREET_GLYPH = " "
STREET_BG = 236   # asphalt gray
INTERIOR_GLYPH = " "
INTERIOR_BG = 238  # concrete gray

#: The 16 ANSI SGR color codes emitted by ``citywalk2d.world.facades`` mapped
#: onto their equivalent 256-color palette indices (0..15).
_SGR16_TO_256: dict[str, int] = {
    "30": 0, "31": 1, "32": 2, "33": 3, "34": 4, "35": 5, "36": 6, "37": 7,
    "90": 8, "91": 9, "92": 10, "93": 11, "94": 12, "95": 13, "96": 14, "97": 15,
    "40": 0, "41": 1, "42": 2, "43": 3, "44": 4, "45": 5, "46": 6, "47": 7,
    "100": 8, "101": 9, "102": 10, "103": 11, "104": 12, "105": 13, "106": 14, "107": 15,
}


def scheme_to_256(scheme) -> tuple[int | None, int | None]:
    """Map a facade ``ColorScheme``'s 16-color ``fg``/``bg`` onto 256 indices.

    Returns ``(fg, bg)`` as ANSI 256-color palette indices (``None`` for
    "no color").  Unknown codes are treated as "no color" rather than raising,
    so a future facade palette can't crash the renderer.
    """
    fg = _SGR16_TO_256.get(scheme.fg) if getattr(scheme, "fg", None) else None
    bg = _SGR16_TO_256.get(scheme.bg) if getattr(scheme, "bg", None) else None
    return fg, bg


def _cell_at(city, facades, wx: int, wy: int) -> Cell:
    """Return the display cell for world cell ``(wx, wy)`` (must be in bounds)."""
    kind = city.cell_type(wx, wy)
    if kind == CellType.STREET:
        return Cell(STREET_GLYPH, bg=STREET_BG)
    if kind == CellType.INTERIOR:
        return Cell(INTERIOR_GLYPH, bg=INTERIOR_BG)
    building = city.building_at(wx, wy)
    facade = facades.facade_for(building.id)
    tile = facade.pattern
    lx = wx - building.rect.x
    ly = wy - building.rect.y
    glyph = tile[ly % len(tile)][lx % len(tile[0])]
    fg, bg = scheme_to_256(facade.scheme)
    return Cell(glyph, fg=fg, bg=bg)


def render_frame(
    city,
    facades,
    player,
    camera: Camera | None = None,
    *,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
) -> FrameBuffer:
    """Build the frame buffer for one frame, camera centered on the player.

    ``camera`` is a pre-built :class:`Camera`; if omitted one is derived from
    ``viewport_width``/``viewport_height`` (defaulting to the renderer's
    defaults) and centered on the player.  Cells outside the world are left as
    empty, uncolored cells (the terminal's own background shows through).
    """
    if camera is None:
        vw = viewport_width if viewport_width is not None else DEFAULT_VIEWPORT_WIDTH
        vh = viewport_height if viewport_height is not None else DEFAULT_VIEWPORT_HEIGHT
        px, py = player.position
        camera = Camera.centered_on(px, py, vw, vh, city.width, city.height)

    fb = FrameBuffer(camera.viewport_width, camera.viewport_height)
    x0, y0 = camera.x, camera.y
    for vy in range(camera.viewport_height):
        for vx in range(camera.viewport_width):
            wx, wy = x0 + vx, y0 + vy
            if city.in_bounds(wx, wy):
                fb.set(vx, vy, _cell_at(city, facades, wx, wy))

    px, py = player.position
    if camera.contains_world(px, py):
        vx, vy = camera.world_to_view(px, py)
        fb.set(vx, vy, Cell(PLAYER_GLYPH, fg=PLAYER_FG, bg=PLAYER_BG))
    return fb


def render(
    city,
    facades,
    player,
    camera: Camera | None = None,
    *,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    color: bool = True,
) -> str:
    """Render one colored top-down frame as a string.

    Convenience wrapper: builds the frame buffer (camera centered on the
    player unless ``camera`` is given) and serializes it with
    :meth:`FrameBuffer.render`.  Pass ``color=False`` for a plain (no-escape)
    frame.
    """
    fb = render_frame(
        city, facades, player, camera,
        viewport_width=viewport_width, viewport_height=viewport_height,
    )
    return fb.render(color=color)
