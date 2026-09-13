"""Wall, window, and facade sampling (DESIGN 2.4, 2.7)."""
from .. import config
from ..assets.palettes import PALETTES
from ..assets.glyphsets import ramp_glyph, luminance
from .palette import scale, fog, add_rgb, brighten
from .lighting import light_contribution


def _hash01(seed, a, b):
    """Deterministic pseudo-random in [0, 1) from integer inputs."""
    h = (seed * 73856093) ^ (a * 19349663) ^ (b * 83492791)
    h = ((h ^ (h // 8192)) * 1274126177) % 2147483648
    return (h % 65536) / 65535.0


def sample_wall(entry, u, v, seed, base, d, lights, wx, wy, wz):
    """Return (glyph, fg, bg) for a wall sample at face coords (u, v)."""
    warm = entry.get("warm", True)
    window_color = PALETTES["window_warm"] if warm else PALETTES["window_cool"]

    if entry.get("window"):
        wu, wus = entry["wu"], entry["wus"]
        wv, wvs = entry["wv"], entry["wvs"]
        ui = int(u / wu)
        vi = int(v / wv)
        in_u = (u - ui * wu) < wus
        in_v = (v - vi * wv) < wvs
        is_window = in_u and in_v
        lit = _hash01(seed, ui, vi) < entry["lit"]
    else:
        # glass: the whole facade is emissive with cell-like variation
        ui = int(u * 6)
        vi = int(v * 8)
        is_window = True
        lit = _hash01(seed, ui, vi) < entry["lit"]

    dark_base = scale(base, 0.5)
    if is_window:
        if lit:
            return "o", window_color, scale(window_color, 0.35)
        return " ", dark_base, dark_base

    # solid facade: night albedo + fog + light pools, textured glyph
    color = fog(base, d)
    if d <= config.FOG_DIST:
        contrib = light_contribution(wx, wy, wz, lights)
        if contrib != (0, 0, 0):
            color = add_rgb(color, contrib)
    tex = _hash01(seed ^ 0x9E37, int(u * 48), int(v * 32))
    gl = min(1.0, luminance(color) + 0.35 * tex)
    glyph = ramp_glyph(gl)
    return glyph, brighten(color, 1.35), color


def render(fb, cam, grid, lights, horizon, type_table, zbuffer=None):
    w, h = fb.width, fb.height
    eye = cam.eye_z()
    for x in range(w):
        camera_x = 2.0 * x / w - 1.0
        hit = _cast(grid, cam, camera_x)
        if hit is None:
            continue
        side, mx, my, d, rdx, rdy = hit
        if zbuffer is not None:
            zbuffer[x] = d
        type_id, height, fz, seed = grid.get(mx, my)
        entry = type_table.get(type_id)
        if entry is None or not entry.get("solid"):
            continue
        wall_top = fz + height
        wall_bot = fz
        screen_top = int(horizon - h * (wall_top - eye) / d)
        screen_bot = int(horizon - h * (wall_bot - eye) / d)
        y0 = max(0, screen_top)
        y1 = min(h - 1, screen_bot)
        if y1 < y0:
            continue
        u = _face_u(side, cam, d, rdx, rdy)
        base = PALETTES[entry["material"]]
        if side == 1:
            base = scale(base, 0.62)
        wx = cam.x + d * rdx
        wy = cam.y + d * rdy
        for y in range(y0, y1 + 1):
            z_at = eye - (horizon - y) * d / h
            v = (wall_top - z_at) / max(1, height)
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            glyph, fg, bg = sample_wall(entry, u, v, seed, base, d, lights,
                                        wx, wy, z_at)
            fb.set(x, y, glyph, fg, bg)


def _cast(grid, cam, camera_x):
    from . import dda
    from .. import config
    return dda.cast_ray(grid, cam.x, cam.y, cam.dir_x, cam.dir_y,
                        cam.plane_x, cam.plane_y, camera_x,
                        config.MAX_DDA_STEPS)


def _face_u(side, cam, d, rdx, rdy):
    from . import dda
    return dda.face_u(side, cam.x, cam.y, d, rdx, rdy)
