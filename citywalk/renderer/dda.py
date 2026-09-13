"""Per-column 2D-DDA raycasting, pure integer-grid stepping (DESIGN 2.3)."""
INF = float("inf")


def cast_ray(grid, pos_x, pos_y, dir_x, dir_y, plane_x, plane_y, camera_x,
             max_steps):
    """Cast one ray through the screen plane.

    Returns (side, map_x, map_y, perp_dist, ray_dir_x, ray_dir_y) on a hit,
    or None if the ray escapes within max_steps (open sky).
    """
    ray_dir_x = dir_x + plane_x * camera_x
    ray_dir_y = dir_y + plane_y * camera_x
    map_x = int(pos_x)
    map_y = int(pos_y)

    delta_x = INF if ray_dir_x == 0.0 else abs(1.0 / ray_dir_x)
    delta_y = INF if ray_dir_y == 0.0 else abs(1.0 / ray_dir_y)

    if ray_dir_x < 0:
        step_x, side_x = -1, (pos_x - map_x) * delta_x
    else:
        step_x, side_x = 1, (map_x + 1.0 - pos_x) * delta_x

    if ray_dir_y < 0:
        step_y, side_y = -1, (pos_y - map_y) * delta_y
    else:
        step_y, side_y = 1, (map_y + 1.0 - pos_y) * delta_y

    for _ in range(max_steps):
        if side_x < side_y:
            side_x += delta_x
            map_x += step_x
            side = 0
        else:
            side_y += delta_y
            map_y += step_y
            side = 1
        if grid.is_solid(map_x, map_y):
            perp = (side_x - delta_x) if side == 0 else (side_y - delta_y)
            if perp < 1e-6:
                perp = 1e-6
            return side, map_x, map_y, perp, ray_dir_x, ray_dir_y
    return None


def face_u(side, pos_x, pos_y, perp, ray_dir_x, ray_dir_y):
    """Fractional coordinate along the hit wall face, in [0, 1)."""
    if side == 0:
        v = pos_y + perp * ray_dir_y
    else:
        v = pos_x + perp * ray_dir_x
    v -= int(v)
    return v if v >= 0 else v + 1.0
