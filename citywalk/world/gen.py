"""Seeded procedural city generator (a compact v1 scene; DESIGN 5.5).

Fully deterministic from the seed. Produces a grid world plus a list of
light sources and a spawn pose. The full multi-zone generator is a later
node; this one builds an enclosed night-city block scene that exercises the
whole renderer (height variation, glass/brick/concrete, lit windows, lamps,
a plaza, and a border skyline).
"""
import random

from .grid import Grid

BRICK = 1
CONCRETE = 2
GLASS = 3
ASPHALT = 4
SIDEWALK = 5
COBBLE = 6
GRASS = 7
WATER = 8
LAMP = 9

BLOCK = 8


def build(seed=20260913, w=48, h=48):
    rng = random.Random(seed)
    g = Grid(w, h)

    # 1. fill with asphalt (open street)
    for y in range(h):
        for x in range(w):
            g.set(x, y, ASPHALT)

    # 2. border ring: tall concrete skyline so rays always terminate
    for x in range(w):
        g.set(x, 0, CONCRETE, height=9, seed=rng.randrange(65536))
        g.set(x, h - 1, CONCRETE, height=9, seed=rng.randrange(65536))
    for y in range(h):
        g.set(0, y, CONCRETE, height=9, seed=rng.randrange(65536))
        g.set(w - 1, y, CONCRETE, height=9, seed=rng.randrange(65536))

    # 3. city blocks of buildings with a central plaza left open
    buildings = []
    blocks = w // BLOCK
    for by in range(1, blocks - 1):
        for bx in range(1, blocks - 1):
            if bx == blocks // 2 and by == blocks // 2:
                continue  # central plaza
            x0 = bx * BLOCK + 1
            y0 = by * BLOCK + 1
            bw = rng.randint(4, BLOCK - 2)
            bh = rng.randint(4, BLOCK - 2)
            height = rng.choice([2, 3, 4, 5, 6, 7, 8])
            typ = rng.choice([BRICK, BRICK, CONCRETE, CONCRETE, GLASS])
            buildings.append((x0, y0, bw, bh, height, typ))

    for (x0, y0, bw, bh, height, typ) in buildings:
        for yy in range(y0, y0 + bh):
            for xx in range(x0, x0 + bw):
                if g.in_bounds(xx, yy):
                    g.set(xx, yy, typ, height=height, seed=rng.randrange(65536))

    # 4. sidewalks: the asphalt immediately around each building becomes sidewalk
    for (x0, y0, bw, bh, height, typ) in buildings:
        for yy in range(y0 - 1, y0 + bh + 1):
            for xx in range(x0 - 1, x0 + bw + 1):
                if g.in_bounds(xx, yy) and g.type_of(xx, yy) == ASPHALT:
                    g.set(xx, yy, SIDEWALK)

    # 5. central plaza (cobble)
    cx = blocks // 2
    cy = blocks // 2
    for yy in range(cy * BLOCK, cy * BLOCK + BLOCK):
        for xx in range(cx * BLOCK, cx * BLOCK + BLOCK):
            if g.in_bounds(xx, yy) and g.type_of(xx, yy) in (ASPHALT, SIDEWALK):
                g.set(xx, yy, COBBLE)

    # 6. street lamps (non-solid markers) + their light sources
    lights = []
    for y in range(2, h - 2, 3):
        for x in range(2, w - 2, 3):
            if g.type_of(x, y) in (ASPHALT, SIDEWALK, COBBLE) and rng.random() < 0.28:
                g.set(x, y, LAMP)
                lights.append((x + 0.5, y + 0.5, 0.4, 255, 196, 120, 2.6, 1.0))

    # spawn at the central street corner, facing east down the street
    spawn = (23.5, 23.5, 0.0)
    return g, lights, spawn
