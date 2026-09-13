"""World subpackage: city grid model (streets, blocks, building footprints).

The grid data layer lives in :mod:`citywalk2d.world.grid` and is re-exported
here so downstream nodes import from a single stable location::

    from citywalk2d.world import generate_city, CellType

    city = generate_city(seed=42)
    city.is_walkable(x, y)
    city.building_at(x, y)
    for b in city.buildings:
        ...
"""

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
    "Rect",
    "generate_city",
]
