"""Unit tests for the player movement module (node G10/4).

Verifies the movement invariants required by the completion contract:

1. a spawned player always starts on a walkable street cell
2. each successful move advances exactly one cell (one axis, unit step)
3. all four canonical directions move correctly
4. movement into a building is rejected (position unchanged)
5. movement out of bounds is rejected (boundary clamping)
"""

import unittest

from citywalk2d.world import (
    CellType,
    Direction,
    Player,
    generate_city,
    spawn_player,
)


DIRECTIONS = (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT)


def find_open_intersection(grid):
    """A street cell whose four orthogonal neighbours are all walkable."""
    for x, y in grid.street_cells():
        if all(
            grid.is_walkable(x + dx, y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            return x, y
    raise AssertionError("no open intersection found in generated city")


def find_street_next_to_building(grid):
    """A (street cell, direction) pair whose target cell is a building."""
    for x, y in grid.street_cells():
        for direction in DIRECTIONS:
            nx, ny = x + direction.dx, y + direction.dy
            if grid.in_bounds(nx, ny) and grid.cell_type(nx, ny) == CellType.BUILDING:
                return (x, y), direction
    raise AssertionError("no street cell adjacent to a building found")


class TestPlayerSpawn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = generate_city(width=48, height=32, seed=12345)

    def test_spawn_starts_on_street(self):
        player = spawn_player(self.grid)
        self.assertTrue(self.grid.is_walkable(player.x, player.y))
        self.assertEqual(
            self.grid.cell_type(player.x, player.y), CellType.STREET,
            "spawn cell must be a street cell",
        )

    def test_spawn_is_deterministic(self):
        a = spawn_player(self.grid, seed=7)
        b = spawn_player(self.grid, seed=7)
        self.assertEqual(a.position, b.position)

    def test_player_rejects_non_walkable_position(self):
        building = self.grid.buildings[0]
        with self.assertRaises(ValueError):
            Player(self.grid, building.rect.x, building.rect.y)


class TestMovement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = generate_city(width=48, height=32, seed=12345)

    def test_each_direction_moves_exactly_one_cell(self):
        x, y = find_open_intersection(self.grid)
        for direction in DIRECTIONS:
            player = Player(self.grid, x, y)
            self.assertTrue(player.move(direction), f"{direction.name} should succeed")
            self.assertEqual(
                player.position, (x + direction.dx, y + direction.dy),
                f"{direction.name} did not move exactly one cell",
            )

    def test_one_cell_per_step_along_street(self):
        x, y = find_open_intersection(self.grid)
        player = Player(self.grid, x, y)
        start_x, start_y = player.position
        for step in range(1, 4):
            self.assertTrue(player.move(Direction.RIGHT))
            self.assertEqual(player.position, (start_x + step, start_y))
            self.assertEqual(player.y, start_y, "horizontal move must not change row")

    def test_blocked_by_building(self):
        grid = generate_city(width=48, height=32, seed=12345, margin=0)
        (x, y), direction = find_street_next_to_building(grid)
        player = Player(grid, x, y)
        self.assertFalse(player.move(direction))
        self.assertEqual(player.position, (x, y), "blocked move must not change position")
        self.assertEqual(
            grid.cell_type(x + direction.dx, y + direction.dy),
            CellType.BUILDING,
            "the blocking cell is a building, not merely out of bounds",
        )

    def test_blocked_at_boundary(self):
        grid = self.grid
        # (0, 0) is a street cell at the map's top-left corner.
        self.assertTrue(grid.is_walkable(0, 0))
        player = Player(grid, 0, 0)
        self.assertFalse(player.move(Direction.LEFT))
        self.assertEqual(player.position, (0, 0))
        self.assertFalse(player.move(Direction.UP))
        self.assertEqual(player.position, (0, 0))
        # moving inward from the corner is still allowed (only out-of-bounds clamps)
        self.assertTrue(player.move(Direction.RIGHT))
        self.assertEqual(player.position, (1, 0))


if __name__ == "__main__":
    unittest.main()
