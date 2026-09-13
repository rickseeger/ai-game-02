"""Central configuration for citywalk2d.

Shared tunables for world generation and the game loop live here so callers
can override defaults from one place instead of reaching into individual
modules.
"""

from __future__ import annotations

#: Terminal viewport defaults (mirror the renderer's own defaults).
DEFAULT_WIDTH = 80
DEFAULT_HEIGHT = 24

#: World generation defaults (mirror citywalk2d.world.generate_city).
CITY_WIDTH = 64
CITY_HEIGHT = 44
CITY_SEED = 1
