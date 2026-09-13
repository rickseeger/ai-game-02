"""Top-down color-ASCII renderer and camera for citywalk2d.

This subpackage owns the game's *picture*: a frame buffer of colored cells
(:mod:`citywalk2d.renderer.framebuffer`), a viewport camera that follows the
player (:mod:`citywalk2d.renderer.camera`), and the scene renderer that
composes the city grid, building facades, and player into a single ANSI
256-color top-down frame (:mod:`citywalk2d.renderer.render`).

Typical use::

    from citywalk2d.renderer import render
    from citywalk2d.world import assign_facades, generate_city, spawn_player

    city = generate_city(seed=42)
    facades = assign_facades(city)
    player = spawn_player(city, seed=7)

    print(render(city, facades, player))                # 80x24 window
    print(render(city, facades, player, viewport_width=32, viewport_height=16))

Or with an explicit camera::

    from citywalk2d.renderer import Camera, render_frame

    px, py = player.position
    camera = Camera.centered_on(px, py, 40, 20, city.width, city.height)
    frame = render_frame(city, facades, player, camera)  # FrameBuffer
    print(frame.render())
"""

from .camera import Camera
from .framebuffer import (
    ANSI_ESCAPE_RE,
    Cell,
    FrameBuffer,
    RESET,
    sgr,
    strip_ansi,
)
from .render import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    INTERIOR_BG,
    INTERIOR_GLYPH,
    PLAYER_BG,
    PLAYER_FG,
    PLAYER_GLYPH,
    STREET_BG,
    STREET_GLYPH,
    render,
    render_frame,
    scheme_to_256,
)

__all__ = [
    "ANSI_ESCAPE_RE",
    "Camera",
    "Cell",
    "DEFAULT_VIEWPORT_HEIGHT",
    "DEFAULT_VIEWPORT_WIDTH",
    "FrameBuffer",
    "INTERIOR_BG",
    "INTERIOR_GLYPH",
    "PLAYER_BG",
    "PLAYER_FG",
    "PLAYER_GLYPH",
    "RESET",
    "STREET_BG",
    "STREET_GLYPH",
    "render",
    "render_frame",
    "scheme_to_256",
    "sgr",
    "strip_ansi",
]
