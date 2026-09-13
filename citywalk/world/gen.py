"""Seeded procedural city generator (DESIGN 5.5) — the full multi-zone night
cityscape that the renderer draws and the player walks.

Deterministic from the seed (``random.Random`` is cross-platform stable, and
the call order is fixed), producing a 96x96 grid world with:

  * a Manhattan street grid (12-18 cell blocks, 2-cell streets, 1-cell
    sidewalks) so the street network is a single connected, navigable component;
  * concentric zoning (plaza / downtown / midtown / residential / industrial,
    plus parks and a north waterfront harbor) with per-zone building height,
    material and window lighting;
  * terrain elevation variation — a sunken harbor channel (floor_z = -2) and
    raised park hills (floor_z = +1);
  * a central plaza with a fountain, a Harbor Hotel landmark on the waterfront,
    and street lamps casting warm light pools;
  * commercial corridors: downtown/midtown blocks get restaurants — a lit
    storefront facade, a striped awning, and tables + chairs on the sidewalk.

Public API
----------
``generate(seed, w, h) -> City``   full metadata (grid, lights, spawn,
                                    restaurants, blocks, landmark).
``build(seed, w, h) -> (grid, lights, spawn)``   renderer-compatible tuple.
"""
import random
from dataclasses import dataclass, field

from .grid import (Grid, BRICK, CONCRETE, GLASS, ASPHALT, SIDEWALK,
                   COBBLE, GRASS, WATER, LAMP, TREE, TABLE, CHAIR, AWNING,
                   FOUNTAIN, SIGN, STOREFRONT)

# --- zones ----------------------------------------------------------------
PLAZA = "plaza"
DOWNTOWN = "downtown"
MIDTOWN = "midtown"
RESIDENTIAL = "residential"
INDUSTRIAL = "industrial"
PARK = "park"
WATERFRONT = "waterfront"

DEFAULT_SIZE = 96
TOP_MARGIN = 4        # rows 0-3: skyline (0), harbor water (1-2), quay (3)
BLOCK_MIN = 12        # min block side, cells
BLOCK_MAX = 18        # max block side, cells
STREET_W = 2          # street width, cells


@dataclass
class Restaurant:
    x: int
    y: int
    w: int
    h: int
    tables: list = field(default_factory=list)   # (x, y) table cells
    chairs: list = field(default_factory=list)   # (x, y) chair cells
    awning: list = field(default_factory=list)   # (x, y) awning cells


@dataclass
class City:
    seed: int
    grid: Grid
    lights: list
    spawn: tuple
    restaurants: list
    blocks: list          # list[(x0, y0, x1, y1, zone)]
    landmark: tuple       # (x, y) of the Harbor Hotel, or None


# --- geometry helpers ------------------------------------------------------

def _grid_lines(rng, start, stop):
    """Street spans (s0, s1) of ``STREET_W`` cells, blocks between them."""
    spans = []
    pos = start
    while True:
        pos += rng.randint(BLOCK_MIN, BLOCK_MAX)
        if pos + STREET_W > stop:
            break
        spans.append((pos, pos + STREET_W))
        pos += STREET_W
    return spans


def _intervals(start, stop, spans):
    """Open intervals (the city blocks) between consecutive street spans."""
    out = []
    cur = start
    for s0, s1 in spans:
        if s0 > cur:
            out.append((cur, s0))
        cur = s1
    if cur < stop:
        out.append((cur, stop))
    return out


# --- zoning ----------------------------------------------------------------

def _assign_zones(nbx, nby, rng):
    """Assign a zone to every (bx, by) block; flip a few to park."""
    cx, cy = nbx // 2, nby // 2
    zones = {}
    for by in range(nby):
        for bx in range(nbx):
            if by == 0:
                zones[(bx, by)] = WATERFRONT
                continue
            d = abs(bx - cx) + abs(by - cy)
            if d == 0:
                zones[(bx, by)] = PLAZA
            elif d == 1:
                zones[(bx, by)] = DOWNTOWN
            elif d <= 3:
                zones[(bx, by)] = MIDTOWN
            elif d <= 5:
                zones[(bx, by)] = RESIDENTIAL
            else:
                zones[(bx, by)] = INDUSTRIAL
    candidates = [k for k, z in zones.items() if z in (RESIDENTIAL, MIDTOWN)]
    rng.shuffle(candidates)
    for k in candidates[:3]:
        zones[k] = PARK
    return zones


def _zone_height(zone, rng):
    return {
        DOWNTOWN: rng.randint(6, 12),
        MIDTOWN: rng.randint(3, 6),
        RESIDENTIAL: rng.randint(1, 3),
        INDUSTRIAL: rng.randint(1, 2),
        WATERFRONT: rng.randint(2, 5),
    }.get(zone, 1)


def _zone_material(zone, rng):
    return {
        DOWNTOWN: rng.choice([GLASS, GLASS, GLASS, CONCRETE, CONCRETE, BRICK]),
        MIDTOWN: rng.choice([CONCRETE, BRICK, CONCRETE, GLASS]),
        RESIDENTIAL: rng.choice([BRICK, BRICK, CONCRETE]),
        INDUSTRIAL: CONCRETE,
        WATERFRONT: rng.choice([BRICK, CONCRETE, GLASS]),
    }.get(zone, BRICK)


def _zone_elevation(zone):
    # terrain variation: parks sit on raised ground, everything else flat.
    return 1 if zone == PARK else 0


# --- drawing passes --------------------------------------------------------

def _border_skyline(g, rng):
    w, h = g.w, g.h
    for x in range(w):
        g.set(x, 0, _skyline_type(rng), height=rng.randint(9, 15),
              seed=rng.randrange(65536))
        g.set(x, h - 1, _skyline_type(rng), height=rng.randint(9, 15),
              seed=rng.randrange(65536))
    for y in range(1, h - 1):
        g.set(0, y, _skyline_type(rng), height=rng.randint(9, 15),
              seed=rng.randrange(65536))
        g.set(w - 1, y, _skyline_type(rng), height=rng.randint(9, 15),
              seed=rng.randrange(65536))


def _skyline_type(rng):
    return rng.choice([CONCRETE, BRICK, CONCRETE, GLASS, BRICK])


def _harbor(g, rng):
    """North waterfront: a sunken water channel + a cobble quay promenade."""
    w, h = g.w, g.h
    for y in (1, 2):
        for x in range(1, w - 1):
            g.set(x, y, WATER, floor_z=-2)
    for x in range(1, w - 1):
        g.set(x, 3, COBBLE)


def _draw_streets(g, vstreets, hstreets):
    w, h = g.w, g.h
    for s0, s1 in vstreets:
        for x in range(s0, s1):
            for y in range(TOP_MARGIN, h - 1):
                g.set(x, y, ASPHALT)
    for t0, t1 in hstreets:
        for y in range(t0, t1):
            for x in range(1, w - 1):
                if g.type_of(x, y) != ASPHALT:
                    g.set(x, y, ASPHALT)
    # 1-cell sidewalks hugging each street
    for s0, s1 in vstreets:
        for y in range(TOP_MARGIN, h - 1):
            if g.type_of(s0 - 1, y) == GRASS:
                g.set(s0 - 1, y, SIDEWALK)
            if g.type_of(s1, y) == GRASS:
                g.set(s1, y, SIDEWALK)
    for t0, t1 in hstreets:
        for x in range(1, w - 1):
            if g.type_of(x, t0 - 1) == GRASS:
                g.set(x, t0 - 1, SIDEWALK)
            if g.type_of(x, t1) == GRASS:
                g.set(x, t1, SIDEWALK)


def _fill_plaza(g, x0, y0, x1, y1, rng):
    lights = []
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if g.type_of(xx, yy) in (GRASS, SIDEWALK, COBBLE):
                g.set(xx, yy, COBBLE)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    g.set(cx, cy, FOUNTAIN)
    lights.append((cx + 0.5, cy + 0.5, 0.3, 64, 220, 255, 3.0, 0.8))
    # signposts at the plaza corners name the district
    for sx in (x0 + 1, x1 - 2):
        for sy in (y0 + 1, y1 - 2):
            if (sx, sy) != (cx, cy):
                g.set(sx, sy, SIGN)
    return lights


def _fill_park(g, x0, y0, x1, y1, rng):
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if g.type_of(xx, yy) == GRASS:
                g.set(xx, yy, GRASS, floor_z=1)
    for yy in range(y0 + 1, y1 - 1):
        for xx in range(x0 + 1, x1 - 1):
            if g.type_of(xx, yy) == GRASS and rng.random() < 0.35:
                g.set(xx, yy, TREE, floor_z=1)


def _fill_waterfront(g, x0, y0, x1, y1, rng):
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if g.type_of(xx, yy) in (GRASS, SIDEWALK):
                g.set(xx, yy, COBBLE)


def _place_restaurants(g, x0, y0, x1, y1, lot, count, rng, restaurants, elev):
    """Restaurants along a block's south frontage (facing the street below)."""
    bx0, bx1 = x0 + 1, x1 - 1
    bw = min(lot - 1, bx1 - bx0)
    if bw < 3:
        return
    positions = [bx0]
    if count > 1 and (bx1 - bx0) >= 2 * bw + 2:
        positions.append(bx1 - bw)
    for lx in positions:
        _make_restaurant(g, lx, y1, bw, x0, x1, elev, rng, restaurants)


def _make_restaurant(g, lx, y1, bw, x0, x1, elev, rng, restaurants):
    depth = 2
    by0 = y1 - 1 - depth
    for yy in range(by0, y1 - 1):
        for xx in range(lx, lx + bw):
            g.set(xx, yy, STOREFRONT, height=2, floor_z=elev,
                  seed=rng.randrange(65536))
    awning = []
    for xx in range(lx, lx + bw):
        if g.type_of(xx, y1 - 1) == SIDEWALK:
            g.set(xx, y1 - 1, AWNING, floor_z=elev)
            awning.append((xx, y1 - 1))
    # tables + chairs flank the awning, clamped to the block's sidewalk span
    tables, chairs = [], []
    sy = y1 - 1
    lo, hi = x0, x1 - 1
    for px in (lx - 1, lx - 2):          # left: table, then chair
        if lo <= px <= hi and g.type_of(px, sy) == SIDEWALK:
            t = TABLE if px == lx - 1 else CHAIR
            g.set(px, sy, t, floor_z=elev)
            (tables if t == TABLE else chairs).append((px, sy))
    for px in (lx + bw, lx + bw + 1):    # right: table, then chair
        if lo <= px <= hi and g.type_of(px, sy) == SIDEWALK:
            t = TABLE if px == lx + bw else CHAIR
            g.set(px, sy, t, floor_z=elev)
            (tables if t == TABLE else chairs).append((px, sy))
    restaurants.append(Restaurant(lx, by0, bw, depth, tables, chairs, awning))


def _lot_taken(g, lx, ly, bw, bh):
    for yy in range(ly, ly + bh):
        for xx in range(lx, lx + bw):
            if g.type_of(xx, yy) == STOREFRONT:
                return True
    return False


def _fill_developed(g, x0, y0, x1, y1, zone, rng, restaurants, elev):
    # ground: cobble courtyard over any remaining grass
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if g.type_of(xx, yy) == GRASS:
                g.set(xx, yy, COBBLE, floor_z=elev)
    bx0, by0, bx1, by1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    lot = rng.choice([4, 5, 6])
    # restaurants need a street on their south side to host the sidewalk tables
    if zone in (DOWNTOWN, MIDTOWN) and y1 < g.h - 1:
        count = 2 if zone == DOWNTOWN else 1
        _place_restaurants(g, x0, y0, x1, y1, lot, count, rng, restaurants, elev)
    for ly in range(by0, by1, lot):
        for lx in range(bx0, bx1, lot):
            bw = min(lot - 1, bx1 - lx)
            bh = min(lot - 1, by1 - ly)
            if bw < 2 or bh < 2:
                continue
            if _lot_taken(g, lx, ly, bw, bh):
                continue
            height = _zone_height(zone, rng)
            typ = _zone_material(zone, rng)
            seed = rng.randrange(65536)
            for yy in range(ly, ly + bh):
                for xx in range(lx, lx + bw):
                    if g.type_of(xx, yy) in (COBBLE, GRASS):
                        g.set(xx, yy, typ, height=height, floor_z=elev,
                              seed=seed)


def _place_landmark(g, blocks, rng):
    waterfront = [b for b in blocks if b[4] == WATERFRONT]
    if not waterfront:
        return None
    w = g.w
    target = min(waterfront, key=lambda b: abs(((b[0] + b[2]) / 2.0) - w / 2.0))
    x0, y0, x1, y1, _ = target
    cx = (x0 + x1) // 2
    half = 4
    for yy in range(y0 + 1, y1 - 1):
        for xx in range(cx - half, cx + half + 1):
            if g.in_bounds(xx, yy) and g.type_of(xx, yy) in (COBBLE, GRASS):
                g.set(xx, yy, GLASS, height=rng.randint(12, 15),
                      seed=rng.randrange(65536))
    return (cx, (y0 + y1) // 2)


def _street_lamps(g, vstreets, hstreets, rng):
    lights = []
    # two lamps at each intersection (opposite corners)
    for s0, s1 in vstreets:
        for t0, t1 in hstreets:
            for cx, cy in ((s0 - 1, t0 - 1), (s1, t1)):
                if g.in_bounds(cx, cy) and g.type_of(cx, cy) in (SIDEWALK, COBBLE):
                    g.set(cx, cy, LAMP)
                    lights.append((cx + 0.5, cy + 0.5, 0.4, 255, 196, 120, 2.6, 1.0))
    # sparse lamps along long street runs
    for s0, s1 in vstreets:
        for y in range(TOP_MARGIN + 8, g.h - 1, 8):
            if g.type_of(s0 - 1, y) == SIDEWALK:
                g.set(s0 - 1, y, LAMP)
                lights.append((s0 - 0.5, y + 0.5, 0.4, 255, 196, 120, 2.6, 1.0))
    for t0, t1 in hstreets:
        for x in range(8, g.w - 1, 8):
            if g.type_of(x, t0 - 1) == SIDEWALK:
                g.set(x, t0 - 1, LAMP)
                lights.append((x + 0.5, t0 - 0.5, 0.4, 255, 196, 120, 2.6, 1.0))
    return lights


def _spawn(g, blocks, rng):
    plaza = [b for b in blocks if b[4] == PLAZA]
    if not plaza:
        plaza = [b for b in blocks if b[4] == WATERFRONT]
    x0, y0, x1, y1, _ = plaza[0]
    return ((x0 + x1) / 2.0 + 0.5, (y0 + y1) / 2.0 + 2.0, 0.0)


# --- top level -------------------------------------------------------------

def generate(seed=20260913, w=DEFAULT_SIZE, h=DEFAULT_SIZE):
    rng = random.Random(seed)
    g = Grid(w, h)

    for y in range(h):
        for x in range(w):
            g.set(x, y, GRASS)

    _border_skyline(g, rng)
    _harbor(g, rng)

    vstreets = _grid_lines(rng, 1, w - 1)
    hstreets = _grid_lines(rng, TOP_MARGIN, h - 1)
    _draw_streets(g, vstreets, hstreets)

    xb = _intervals(1, w - 1, vstreets)
    yb = _intervals(TOP_MARGIN, h - 1, hstreets)
    zones = _assign_zones(len(xb), len(yb), rng)
    blocks = []
    for by, (y0, y1) in enumerate(yb):
        for bx, (x0, x1) in enumerate(xb):
            blocks.append((x0, y0, x1, y1, zones[(bx, by)]))

    restaurants = []
    lights = []
    for x0, y0, x1, y1, zone in blocks:
        if zone == PLAZA:
            lights += _fill_plaza(g, x0, y0, x1, y1, rng)
        elif zone == PARK:
            _fill_park(g, x0, y0, x1, y1, rng)
        elif zone == WATERFRONT:
            _fill_waterfront(g, x0, y0, x1, y1, rng)
        else:
            _fill_developed(g, x0, y0, x1, y1, zone, rng, restaurants,
                            _zone_elevation(zone))

    landmark = _place_landmark(g, blocks, rng)
    lights += _street_lamps(g, vstreets, hstreets, rng)
    for r in restaurants:
        lights.append((r.x + r.w / 2.0, r.y + 0.5, 0.3, 255, 170, 90, 3.0, 0.9))

    spawn = _spawn(g, blocks, rng)
    return City(seed, g, lights, spawn, restaurants, blocks, landmark)


def build(seed=20260913, w=DEFAULT_SIZE, h=DEFAULT_SIZE):
    """Renderer-compatible wrapper: (grid, lights, spawn)."""
    city = generate(seed, w, h)
    return city.grid, city.lights, city.spawn
