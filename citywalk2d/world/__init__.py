"""World subpackage: city grid model, building facades, and the player.

The grid data layer lives in :mod:`citywalk2d.world.grid`, the facade data
layer lives in :mod:`citywalk2d.world.facades`, and the player/movement layer
lives in :mod:`citywalk2d.world.player`; all three are re-exported here so
downstream nodes import from a single stable location::

    from citywalk2d.world import generate_city, assign_facades, spawn_player

    city = generate_city(seed=42)
    city.is_walkable(x, y)
    city.building_at(x, y)
    for b in city.buildings:
        ...

    facades = assign_facades(city)
    facades.facade_for(0).render(w, h)

    player = spawn_player(city)
    player.move(Direction.RIGHT)
"""

from .facades import (
    ColorScheme,
    Facade,
    FacadeMap,
    PATTERNS,
    SCHEMES,
    assign_facades,
    render_colored_city,
)
from .grid import (
    Block,
    Building,
    CellType,
    CityGrid,
    Rect,
    generate_city,
)
from .player import (
    Direction,
    Player,
    spawn_player,
)

__all__ = [
    "Block",
    "Building",
    "CellType",
    "CityGrid",
    "ColorScheme",
    "Direction",
    "Facade",
    "FacadeMap",
    "PATTERNS",
    "Player",
    "Rect",
    "SCHEMES",
    "assign_facades",
    "generate_city",
    "render_colored_city",
    "spawn_player",
]
