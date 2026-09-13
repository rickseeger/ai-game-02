"""Engine subpackage: the assembled game loop (node G10/7).

The engine is the glue that wires the world (grid, facades, player), input,
and renderer into a single running game loop.  All behaviour lives in
:mod:`citywalk2d.engine.loop` and is re-exported here so downstream callers
import from one stable location::

    from citywalk2d.engine import build_city, run_script, run_interactive

    city, facades, player = build_city(seed=42)
    run_script(city, facades, player, [Action.RIGHT, Action.DOWN, Action.QUIT])
"""

from .loop import (
    ACTION_BY_TEXT,
    ANSI_CLEAR,
    ANSI_HIDE_CURSOR,
    ANSI_SHOW_CURSOR,
    apply_action,
    build_city,
    parse_script_action,
    run,
    run_interactive,
    run_script,
)

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
