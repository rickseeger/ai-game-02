"""Grid world: a flat array of type ids plus parallel height/floor/seed arrays,
with the type table that maps type_id -> material and behavior (DESIGN 5.2)."""
from array import array


# type_id -> { name, solid, material, window params, ... }
TYPE_TABLE = {
    0: {"name": "void", "solid": False},
    1: {"name": "brick", "solid": True, "material": "brick", "window": True,
        "wu": 0.14, "wus": 0.08, "wv": 0.18, "wvs": 0.10, "lit": 0.35,
        "warm": True},
    2: {"name": "concrete", "solid": True, "material": "concrete", "window": True,
        "wu": 0.16, "wus": 0.09, "wv": 0.20, "wvs": 0.12, "lit": 0.22,
        "warm": True},
    3: {"name": "glass", "solid": True, "material": "glass", "window": False,
        "lit": 0.50, "warm": False},
    4: {"name": "asphalt", "solid": False},
    5: {"name": "sidewalk", "solid": False},
    6: {"name": "cobble", "solid": False},
    7: {"name": "grass", "solid": False},
    8: {"name": "water", "solid": False},
    9: {"name": "lamp", "solid": False},
}


class Grid:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        n = w * h
        self.types = array("H", [0]) * n
        self.height = array("b", [0]) * n
        self.floor_z = array("b", [0]) * n
        self.seed = array("H", [0]) * n

    def idx(self, x, y):
        return y * self.w + x

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, type_id, height=0, floor_z=0, seed=0):
        i = self.idx(x, y)
        self.types[i] = type_id
        self.height[i] = height
        self.floor_z[i] = floor_z
        self.seed[i] = seed

    def get(self, x, y):
        if not self.in_bounds(x, y):
            return None
        i = self.idx(x, y)
        return (self.types[i], self.height[i], self.floor_z[i], self.seed[i])

    def type_of(self, x, y):
        if not self.in_bounds(x, y):
            return 0
        return self.types[self.idx(x, y)]

    def is_solid(self, x, y):
        if not self.in_bounds(x, y):
            return False
        t = self.types[self.idx(x, y)]
        entry = TYPE_TABLE.get(t)
        return bool(entry and entry.get("solid"))
