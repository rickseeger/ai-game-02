"""Floor casting (Lodev), at half horizontal resolution, with materials,
fog, and light pools (DESIGN 2.5)."""
from .. import config
from ..assets.palettes import PALETTES
from ..assets.glyphsets import ramp_glyph, luminance
from .palette import fog, add_rgb, scale
from .lighting import light_contribution

# floor material name per floor-bearing cell type id (see world/grid.py)
FLOOR_MATERIAL = {
    4: "asphalt", 5: "sidewalk", 6: "cobble", 7: "grass", 8: "water",
    17: "cobble",
}

# placeable decor on floor cells: type id -> (glyph, fg palette name).
# Non-solid markers the floorcaster draws in place of the ramp glyph.
DECOR = {
    9: ("*", "lamp_warm"),      # street lamp head
    10: ("T", "tree"),          # park tree
    11: ("n", "table"),         # restaurant table
    12: ("h", "chair"),         # restaurant chair
    13: ("=", "awning_red"),    # restaurant awning (color varies by cell seed)
    14: ("0", "neon_cyan"),     # plaza fountain
    15: ("|", "neon_yellow"),   # district signpost
    17: ("@", "neon_green"),    # Maya's rooftop garden (mission target)
}


def inverse_project(cam, x, y, horizon, w, h):
    """Inverse-project a screen column/row to a floor world point.

    Returns (wx, wy, row_distance) or None for rows at/above the horizon.
    This is the pure math tested in tests/test_floorcast.py.
    """
    dirx0 = cam.dir_x - cam.plane_x
    diry0 = cam.dir_y - cam.plane_y
    dirx1 = cam.dir_x + cam.plane_x
    diry1 = cam.dir_y + cam.plane_y
    p = y - horizon
    if p <= 0:
        return None
    row_dist = config.EYE_HEIGHT * h / p
    t = (x + 0.5) / w
    wx = cam.x + row_dist * (dirx0 + (dirx1 - dirx0) * t)
    wy = cam.y + row_dist * (diry0 + (diry1 - diry0) * t)
    return wx, wy, row_dist


def render(fb, cam, grid, lights, horizon):
    w, h = fb.width, fb.height
    step = config.FLOOR_STEP
    eye = cam.eye_z()
    for y in range(max(0, horizon), h):
        p = y - horizon
        if p <= 0:
            continue
        row_dist = config.EYE_HEIGHT * h / p
        # inverse projection step across the row (Lodev)
        dirx0 = cam.dir_x - cam.plane_x
        diry0 = cam.dir_y - cam.plane_y
        dirx1 = cam.dir_x + cam.plane_x
        diry1 = cam.dir_y + cam.plane_y
        sx = row_dist * (dirx1 - dirx0) / w
        sy = row_dist * (diry1 - diry0) / w
        fx = cam.x + row_dist * dirx0
        fy = cam.y + row_dist * diry0
        near = row_dist <= config.FOG_DIST
        for x in range(0, w, step):
            cx = int(fx)
            cy = int(fy)
            cell = grid.get(cx, cy)
            type_id = cell[0] if cell else 0
            floor_z = cell[2] if cell else 0
            seed = cell[3] if cell else 0
            mat = FLOOR_MATERIAL.get(type_id, "asphalt")
            base = PALETTES.get(mat, PALETTES["asphalt"])
            # elevation hint: raised cells brighten, sunken cells darken
            if floor_z > 0:
                base = add_rgb(base, (6 * floor_z, 6 * floor_z, 6 * floor_z))
            elif floor_z < 0:
                base = scale(base, 0.72)
            color = fog(base, row_dist)
            if near:
                contrib = light_contribution(fx, fy, 0.0, lights)
                if contrib != (0, 0, 0):
                    color = add_rgb(color, contrib)
            decor = DECOR.get(type_id)
            if decor:
                glyph, fg_name = decor
                if type_id == 13:  # awning: alternate red/green by cell seed
                    fg_name = "awning_red" if (seed % 2 == 0) else "awning_green"
                fg = PALETTES[fg_name]
                bg = color
            else:
                lum = luminance(color)
                glyph = ramp_glyph(lum)
                fg = add_rgb(color, (12, 12, 12))
                bg = color
            end = min(w, x + step)
            for xx in range(x, end):
                fb.set(xx, y, glyph, fg, bg)
            fx += sx * step
            fy += sy * step
