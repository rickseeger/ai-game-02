"""Main game loop for citywalk2d (node G10/7).

The engine is the glue that assembles the previously-built layers -- the city
grid, building facades, player movement, keyboard input, and the top-down
renderer -- into a single running game:

    init grid + facades + player
    render the viewport
    read an action (WASD / arrows / quit)
    move the player one cell (or quit)
    re-render
    loop until quit

The loop is deliberately I/O-agnostic so the same core can be driven two ways:

* interactively, from a real keyboard (:func:`run_interactive`), and
* deterministically, from a scripted sequence of ``Action`` values
  (:func:`run_script`), which is what the integration test and the
  ``--script`` entrypoint use.

Nothing here re-implements grid generation, movement, input decoding, or
rendering -- the engine only *assembles* the committed modules.
"""

from __future__ import annotations

import os
import sys

from .. import config
from ..input import Action, KeyReader
from ..renderer import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    RESET,
    render,
)
from ..world import assign_facades, generate_city, spawn_player

__all__ = [
    "ACTION_BY_TEXT",
    "ANSI_CLEAR",
    "ANSI_HIDE_CURSOR",
    "ANSI_SHOW_CURSOR",
    "apply_action",
    "build_city",
    "parse_script_action",
    "run",
    "run_interactive",
    "run_script",
]

#: ANSI sequences used by the interactive runner for full-screen redraw.
ANSI_CLEAR = "\x1b[2J\x1b[H"
ANSI_HIDE_CURSOR = "\x1b[?25l"
ANSI_SHOW_CURSOR = "\x1b[?25h"

#: Human-readable script tokens -> their canonical Action.  Scripts may use
#: direction names or the WASD / quit letters the game itself recognises.
ACTION_BY_TEXT: dict[str, Action] = {
    "up": Action.UP, "w": Action.UP,
    "down": Action.DOWN, "s": Action.DOWN,
    "left": Action.LEFT, "a": Action.LEFT,
    "right": Action.RIGHT, "d": Action.RIGHT,
    "quit": Action.QUIT, "q": Action.QUIT, "exit": Action.QUIT,
}


def build_city(width=None, height=None, seed=None, player_seed=None):
    """Build the whole world in one call: city grid, facades, and a player.

    All three layers are created deterministically from ``seed`` (defaulting
    to :data:`citywalk2d.config.CITY_SEED`); ``player_seed`` is forwarded to
    :func:`citywalk2d.world.spawn_player` (``None`` spawns on the first street
    cell, the top-left corner).
    """
    if width is None:
        width = config.CITY_WIDTH
    if height is None:
        height = config.CITY_HEIGHT
    if seed is None:
        seed = config.CITY_SEED
    city = generate_city(width=width, height=height, seed=seed)
    facades = assign_facades(city)
    player = spawn_player(city, seed=player_seed)
    return city, facades, player


def apply_action(player, action) -> bool:
    """Apply one ``Action`` to the player; return ``False`` only for ``QUIT``.

    Movement actions advance the player exactly one cell (rejected moves leave
    the position unchanged); an unrecognised ``None`` action is a no-op that
    still counts as "keep running".
    """
    if action is Action.QUIT:
        return False
    if action is not None and action.is_movement:
        player.move(action.direction)
    return True


def parse_script_action(text: str):
    """Map one script line to an ``Action`` (``None`` for blank/comment/unknown).

    Accepts direction names (``up``/``down``/``left``/``right``), the WASD
    letters, and the quit words (``quit``/``q``/``exit``), case-insensitively.
    Blank lines and ``#`` comments map to ``None`` and are skipped by callers.
    """
    token = text.strip().lower()
    if not token or token.startswith("#"):
        return None
    return ACTION_BY_TEXT.get(token)


def run(
    city,
    facades,
    player,
    *,
    read_action,
    write_frame,
    viewport_width=None,
    viewport_height=None,
    color=True,
):
    """Run the game loop with injected I/O; returns the number of frames drawn.

    ``read_action`` is a zero-arg callable returning the next ``Action`` (or
    ``None`` for an unrecognised key); ``write_frame`` is a one-arg callable
    receiving each rendered frame string.  The loop draws one frame, then
    repeatedly reads an action, applies it to the player, and re-draws, until
    ``read_action`` returns :data:`Action.QUIT`.
    """
    width = viewport_width if viewport_width is not None else DEFAULT_VIEWPORT_WIDTH
    height = viewport_height if viewport_height is not None else DEFAULT_VIEWPORT_HEIGHT

    def draw() -> str:
        return render(
            city, facades, player,
            viewport_width=width, viewport_height=height, color=color,
        )

    frames = 0
    write_frame(draw())
    frames += 1
    while True:
        action = read_action()
        if action is Action.QUIT:
            break
        if action is not None and action.is_movement:
            player.move(action.direction)
        write_frame(draw())
        frames += 1
    return frames


def run_script(
    city,
    facades,
    player,
    actions,
    *,
    write_frame=print,
    viewport_width=None,
    viewport_height=None,
    color=False,
):
    """Run the loop driven by an iterable of ``Action`` (stops at exhaustion).

    The iterable is consumed in order; the loop halts when it yields
    :data:`Action.QUIT` or runs out, so a script need not end with an explicit
    quit.  Returns the number of frames drawn (one initial, plus one per step).
    """
    iterator = iter(actions)
    return run(
        city, facades, player,
        read_action=lambda: next(iterator, Action.QUIT),
        write_frame=write_frame,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        color=color,
    )


def _enable_windows_ansi() -> None:
    """Enable ANSI escape processing on Windows consoles (no-op elsewhere)."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass  # never let ANSI setup break the game


def run_interactive(
    city,
    facades,
    player,
    *,
    viewport_width=None,
    viewport_height=None,
    color=True,
    out=None,
):
    """Run the real terminal game loop: raw keys in, full-screen frames out.

    Drops the terminal into cbreak mode (via :class:`citywalk2d.input.KeyReader`)
    and redraws the viewport in place each frame, hiding the cursor and clearing
    the screen when color/ANSI is enabled.  The terminal is always restored on
    exit, and the player's final position is available afterwards.
    """
    out = out if out is not None else sys.stdout
    if color:
        _enable_windows_ansi()
    width = viewport_width if viewport_width is not None else DEFAULT_VIEWPORT_WIDTH
    height = viewport_height if viewport_height is not None else DEFAULT_VIEWPORT_HEIGHT

    if color:
        def write_frame(frame: str) -> None:
            out.write(ANSI_CLEAR)
            out.write(frame)
            out.write("\n")
            out.flush()
    else:
        def write_frame(frame: str) -> None:
            out.write(frame)
            out.write("\n")
            out.flush()

    if color:
        out.write(ANSI_HIDE_CURSOR)
        out.flush()
    try:
        with KeyReader() as keys:
            return run(
                city, facades, player,
                read_action=keys.read,
                write_frame=write_frame,
                viewport_width=width,
                viewport_height=height,
                color=color,
            )
    finally:
        if color:
            out.write(ANSI_SHOW_CURSOR)
            out.write(RESET)
            out.write("\n")
            out.flush()
