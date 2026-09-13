"""Sprite / billboard rendering for moving life (cars, pedestrians, pets).

Classic Lodev sprite casting: each entity is transformed through the camera
plane, its perpendicular depth is compared against the per-column wall
z-buffer (so walls occlude sprites), and a shaded billboard is drawn into the
cell framebuffer using the same fog + light-pool model as walls and floors.

Cars get a roof band, a dark window band, a body band, and emissive running
lights at the bottom corners; pedestrians get a head + coat; pets a small
body + head. All glyphs are single-width ASCII (same constraint as the
renderer). Entities behind the camera, inside the near clip, or beyond the
fog distance are culled so the pass stays O(visible entities).
"""
from .. import config
from ..assets.palettes import PALETTES
from .palette import fog, add_rgb, brighten, scale
from .lighting import light_contribution
from ..world.entities import CAR, PEDESTRIAN, PET, BODY

NEAR_CLIP = 0.2          # skip sprites closer than this (inside the camera)
_MAX_SPRITE_W = 20       # clamp absurdly wide billboards


def project(cam, sx, sy):
    """Project world point (sx, sy) through the camera plane.

    Returns ``(screen_x_fractional, depth)`` where ``depth`` is the
    perpendicular distance along the view axis, or ``None`` when the point is
    at or behind the camera plane. Pure math, tested directly.
    """
    inv = 1.0 / (cam.plane_x * cam.dir_y - cam.dir_x * cam.plane_y)
    tx = inv * (cam.dir_y * (sx - cam.x) - cam.dir_x * (sy - cam.y))
    ty = inv * (-cam.plane_y * (sx - cam.x) + cam.plane_x * (sy - cam.y))
    if ty <= 0.0:
        return None
    return tx, ty


def render(fb, cam, lights, horizon, life, zbuffer):
    if life is None or not getattr(life, "entities", None):
        return
    w, h = fb.width, fb.height
    visible = []
    for e in life.entities:
        p = project(cam, e.x, e.y)
        if p is None:
            continue
        tx, ty = p
        if ty < NEAR_CLIP or ty > config.FOG_DIST + 2.0:
            continue
        visible.append((ty, e, tx))
    # draw far-to-near so nearer sprites paint over farther ones
    visible.sort(key=lambda item: item[0], reverse=True)
    for ty, e, tx in visible:
        _draw(fb, cam, lights, horizon, w, h, zbuffer, e, tx, ty)


def _draw(fb, cam, lights, horizon, w, h, zbuffer, e, tx, ty):
    body = BODY[e.kind]
    sz = body["height"]
    fz = e.z
    eye = cam.eye_z()
    top = fz + sz
    screen_top = horizon - h * (top - eye) / ty
    screen_bot = horizon - h * (fz - eye) / ty
    y0 = int(screen_top)
    y1 = int(screen_bot)
    if y1 < y0:
        return
    if y0 < 0:
        y0 = 0
    if y1 >= h:
        y1 = h - 1
    rows = y1 - y0 + 1
    if rows <= 0:
        return
    sprite_w = max(1, int(rows * body["aspect"]))
    if sprite_w > _MAX_SPRITE_W:
        sprite_w = _MAX_SPRITE_W
    center_x = int((w / 2.0) * (1.0 + tx / ty))
    x0 = center_x - sprite_w // 2
    x1 = x0 + sprite_w

    # Shade the body's bands once (depth is constant across the billboard).
    near = ty <= config.FOG_DIST
    glow = light_contribution(e.x, e.y, fz + sz * 0.5, lights) if near else (0, 0, 0)

    def shade(base):
        col = fog(base, ty)
        if glow != (0, 0, 0):
            col = add_rgb(col, glow)
        return col

    roof = body_c = window_c = bumper = light_c = head_c = coat_c = None
    if e.kind == CAR:
        roof = shade(scale(PALETTES[e.color], 0.5))
        body_c = shade(PALETTES[e.color])
        window_c = shade(PALETTES["window_cool"])
        bumper = shade(scale(PALETTES[e.color], 0.6))
        light_c = PALETTES["lamp_warm"]
    elif e.kind == PEDESTRIAN:
        head_c = shade(PALETTES["ped_head"])
        coat_c = shade(PALETTES[e.color])
    else:  # PET
        head_c = shade(PALETTES[e.color])
        body_c = shade(PALETTES[e.color])

    for sx in range(max(0, x0), min(w, x1)):
        if ty >= zbuffer[sx]:
            continue
        u = (sx - x0) / float(sprite_w)
        for sy in range(y0, y1 + 1):
            z_at = eye - (horizon - sy) * ty / h
            v = (z_at - fz) / sz
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            glyph, fg, bg = _sample(e, u, v, roof, body_c, window_c, bumper,
                                    light_c, head_c, coat_c)
            fb.set(sx, sy, glyph, fg, bg)


def _sample(e, u, v, roof, body_c, window_c, bumper, light_c, head_c, coat_c):
    """Map fractional (u, v) on the billboard to (glyph, fg, bg)."""
    if e.kind == CAR:
        if v > 0.70:
            return " ", roof, roof                       # roof band
        if v > 0.42:
            return ":", window_c, window_c               # window band
        if v > 0.14:
            return e.glyph, brighten(body_c, 1.25), body_c
        # running lights: bright warm dots at the two bottom corners
        if u < 0.25 or u > 0.75:
            return "*", light_c, light_c
        return " ", bumper, bumper
    if e.kind == PEDESTRIAN:
        if v > 0.78:
            return "o", brighten(head_c, 1.2), head_c    # head
        return e.glyph, brighten(coat_c, 1.25), coat_c   # coat/body
    # pet
    if v > 0.62:
        return "o", brighten(head_c, 1.2), head_c
    return e.glyph, brighten(body_c, 1.25), body_c
