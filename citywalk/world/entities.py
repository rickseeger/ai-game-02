"""Moving city life (DESIGN 5.1, node 4): cars, pedestrians, and pets.

A deterministic, seeded population that makes the night city feel alive:

  * **cars** drive the street grid (asphalt cells only), turning at
    intersections;
  * **pedestrians** walk the sidewalk network (sidewalk / cobble cells);
  * **pets** wander sidewalks, plazas, and park grass (sidewalk / cobble /
    grass cells).

Movement is a cell-to-cell random walk with continuous interpolation between
adjacent cell *centers*. Each entity therefore always stays on terrain legal
for its kind, never leaves the grid, never enters a solid cell, and needs no
collision broadphase or pathfinding -- the per-frame cost is O(population) of
cheap integer + float arithmetic, well inside the 30 fps frame budget.

Every decision (spawn placement, speed, color, turn choice, pause) is drawn
from a ``random.Random`` so a fixed seed reproduces the exact same population
and, given the same ``dt`` sequence, the exact same motion -- on Linux and
Windows alike (``random.Random`` is cross-platform stable).
"""
import random
from dataclasses import dataclass

from .grid import ASPHALT, SIDEWALK, COBBLE, GRASS

# --- entity kinds ---------------------------------------------------------
CAR = "car"
PEDESTRIAN = "pedestrian"
PET = "pet"

# cardinal headings: 0 = north, 1 = east, 2 = south, 3 = west (y grows down)
DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)

# per-kind body profile used by the sprite renderer: world height in cells,
# width-to-height aspect, body glyph, and default palette color.
BODY = {
    CAR: {"height": 0.55, "aspect": 2.2, "glyph": "#", "color": "car_taxi"},
    PEDESTRIAN: {"height": 0.85, "aspect": 0.6, "glyph": "A", "color": "pedestrian"},
    PET: {"height": 0.35, "aspect": 1.1, "glyph": "q", "color": "pet"},
}

# per-kind set of cell types an entity may stand on (from world.grid).
WALKABLE = {
    CAR: frozenset((ASPHALT,)),
    PEDESTRIAN: frozenset((SIDEWALK, COBBLE)),
    PET: frozenset((SIDEWALK, COBBLE, GRASS)),
}

# movement speed range (cells/second), sampled per entity.
SPEED_RANGE = {
    CAR: (1.4, 2.8),
    PEDESTRIAN: (0.5, 1.1),
    PET: (0.6, 1.2),
}

# probability an entity keeps going straight when it reaches a junction.
STRAIGHT_BIAS = {CAR: 0.7, PEDESTRIAN: 0.6, PET: 0.5}

# probability an entity pauses briefly after arriving at a cell.
PAUSE_CHANCE = {CAR: 0.0, PEDESTRIAN: 0.12, PET: 0.18}

# palette colors an entity's body may take (entries live in assets/palettes.py).
COLORS = {
    CAR: ("car_taxi", "car_sedan", "car_blue", "car_white"),
    PEDESTRIAN: ("pedestrian", "ped_blue", "ped_red"),
    PET: ("pet", "pet_black", "pet_white"),
}

# population targets for the default 96x96 city (clamped to available cells).
COUNTS = {CAR: 20, PEDESTRIAN: 40, PET: 14}


@dataclass
class Entity:
    """One moving body: continuous position, heading, and walk-interpolation
    state between its anchor cell and target cell."""
    kind: str
    x: float            # continuous position (grid cell units)
    y: float
    z: float            # continuous floor elevation (interpolated)
    dir: int            # heading 0..3
    speed: float        # cells/second
    color: str          # palette name for the body
    glyph: str          # ASCII glyph for the body
    rng: "random.Random"
    ax: int = 0         # anchor cell (already reached)
    ay: int = 0
    bx: int = 0         # target cell (moving toward)
    by: int = 0
    t: float = 0.0      # progress 0..1 from anchor center to target center
    pause: float = 0.0  # remaining idle time, seconds


class LifeSystem:
    """The city's ambient population and its cheap per-frame update."""

    def __init__(self, grid, seed=20260913):
        self.grid = grid
        self.seed = seed
        self.entities = []
        self._spawn(random.Random(seed))

    # -- spawning ----------------------------------------------------------
    def _cells_of(self, kind):
        allowed = WALKABLE[kind]
        g = self.grid
        return [(x, y) for y in range(g.h) for x in range(g.w)
                if g.type_of(x, y) in allowed]

    def _dirs(self, kind, x, y):
        """Heading indices whose neighbor cell is legal for ``kind``."""
        allowed = WALKABLE[kind]
        g = self.grid
        return [d for d in range(4)
                if g.in_bounds(x + DX[d], y + DY[d])
                and g.type_of(x + DX[d], y + DY[d]) in allowed]

    def _spawn(self, rng):
        for kind in (CAR, PEDESTRIAN, PET):
            cells = self._cells_of(kind)
            rng.shuffle(cells)
            for x, y in cells[:COUNTS[kind]]:
                dirs = self._dirs(kind, x, y)
                if not dirs:
                    continue
                d = rng.choice(dirs)
                e = Entity(
                    kind=kind,
                    x=x + 0.5, y=y + 0.5,
                    z=float(self.grid.floor_z[self.grid.idx(x, y)]),
                    dir=d,
                    speed=rng.uniform(*SPEED_RANGE[kind]),
                    color=rng.choice(COLORS[kind]),
                    glyph=BODY[kind]["glyph"],
                    rng=random.Random(rng.getrandbits(31)),
                    ax=x, ay=y,
                    bx=x + DX[d], by=y + DY[d],
                    t=0.0, pause=0.0,
                )
                self.entities.append(e)

    # -- simulation --------------------------------------------------------
    def update(self, dt):
        """Advance every entity by ``dt`` seconds."""
        if not (dt > 0.0):
            return
        for e in self.entities:
            self._step(e, dt)

    def _step(self, e, dt):
        if e.pause > 0.0:
            e.pause -= dt
            if e.pause < 0.0:
                e.pause = 0.0
            return
        e.t += e.speed * dt
        while e.t >= 1.0:
            e.t -= 1.0
            e.ax, e.ay = e.bx, e.by
            d = self._choose_dir(e)
            if d is None:               # dead end: park and pause a moment
                e.t = 0.0
                e.bx, e.by = e.ax, e.ay
                e.pause = self._pause_for(e)
                break
            e.dir = d
            e.bx = e.ax + DX[d]
            e.by = e.ay + DY[d]
        g = self.grid
        az = g.floor_z[g.idx(e.ax, e.ay)]
        bz = g.floor_z[g.idx(e.bx, e.by)]
        e.x = e.ax + 0.5 + (e.bx - e.ax) * e.t
        e.y = e.ay + 0.5 + (e.by - e.ay) * e.t
        e.z = az + (bz - az) * e.t

    def _choose_dir(self, e):
        """Pick the next heading: mostly straight, otherwise a legal turn."""
        cands = self._dirs(e.kind, e.ax, e.ay)
        if not cands:
            return None
        reverse = (e.dir + 2) % 4
        forward = [d for d in cands if d != reverse]
        pool = forward if forward else cands
        bias = STRAIGHT_BIAS[e.kind]
        if e.dir in pool and (len(pool) == 1 or e.rng.random() < bias):
            return e.dir
        turns = [d for d in pool if d != e.dir]
        return e.rng.choice(turns if turns else pool)

    def _pause_for(self, e):
        if e.rng.random() < PAUSE_CHANCE[e.kind]:
            return e.rng.uniform(0.4, 1.8)
        return 0.0
