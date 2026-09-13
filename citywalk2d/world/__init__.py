"""World subpackage: city grid model and building facades.

The grid data layer lives in :mod:`citywalk2d.world.grid` and the facade data
layer lives in :mod:`citywalk2d.world.facades`; both are re-exported here so
downstream nodes import from a single stable location::

    from citywalk2d.world import generate_city, assign_facades

    city = generate_city(seed=42)
    city.is_walkable(x, y)
    city.building_at(x, y)
    for b in city.buildings:
        ...

    facades = assign_facades(city)
    facades.facade_for(0).render(w, h)
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

__all__ = [
    "Block",
    "Building",
    "CellType",
    "CityGrid",
    "ColorScheme",
    "Facade",
    "FacadeMap",
    "PATTERNS",
    "Rect",
    "SCHEMES",
    "assign_facades",
    "generate_city",
    "render_colored_city",
]
