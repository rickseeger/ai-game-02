"""Primary mission tests (node 6): stages, objective tracking, completion,
compass wayfinding, the soft deadline, the credit reward, and integration
with the generated city and the survival loop.

Mirrors DESIGN 7.3: "Find Maya at the rooftop garden of the Harbor Hotel
before 2:00 AM" -- three stages (find the hotel -> ride to the rooftop ->
talk to Maya), a tracked objective with a compass hint, a satisfiable
completion (talk to Maya -> complete + credits), and a soft deadline that
resets rather than game-overs.
"""
import math
import os
import sys
import unittest
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk import config
from citywalk.world import gen
from citywalk.world.grid import ROOFTOP
from citywalk.world.quests import FIND_MAYA, Quest, direction_label
from citywalk.world.survival import Needs


def _reachable(grid, start):
    sx, sy = int(start[0]), int(start[1])
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if grid.in_bounds(nx, ny) and not grid.is_solid(nx, ny) \
                    and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


class TestDefinition(unittest.TestCase):
    def test_definition_has_three_stages_and_reward(self):
        self.assertEqual(len(FIND_MAYA["stages"]), 3)
        ids = [s["id"] for s in FIND_MAYA["stages"]]
        self.assertEqual(ids, ["find_hotel", "reach_rooftop", "talk_maya"])
        self.assertGreater(FIND_MAYA["reward_credits"], 0)
        self.assertIn("deadline", FIND_MAYA)


class TestStageProgression(unittest.TestCase):
    def _quest(self):
        return Quest(FIND_MAYA, (10.0, 10.0))

    def test_starts_at_find_hotel_not_complete(self):
        q = self._quest()
        self.assertEqual(q.stage_id, "find_hotel")
        self.assertEqual(q.objective, "Find the Harbor Hotel")
        self.assertFalse(q.is_complete())

    def test_far_away_position_does_not_advance(self):
        q = self._quest()
        self.assertIsNone(q.on_position(0.0, 0.0))
        self.assertEqual(q.stage_id, "find_hotel")

    def test_position_within_range_advances_to_reach_rooftop(self):
        q = self._quest()
        self.assertIsNotNone(q.on_position(11.0, 10.0))
        self.assertEqual(q.stage_id, "reach_rooftop")
        self.assertIn("Ride to the rooftop", q.objective)

    def test_position_at_exact_range_advances(self):
        q = self._quest()
        self.assertIsNotNone(q.on_position(13.0, 10.0))  # 3.0 cells, boundary
        self.assertEqual(q.stage_id, "reach_rooftop")

    def test_position_just_outside_range_does_not_advance(self):
        q = self._quest()
        self.assertIsNone(q.on_position(13.1, 10.0))
        self.assertEqual(q.stage_id, "find_hotel")

    def test_interact_far_away_is_noop(self):
        q = self._quest()
        q.on_position(11.0, 10.0)   # now reach_rooftop
        self.assertIsNone(q.on_interact(0.0, 0.0))
        self.assertEqual(q.stage_id, "reach_rooftop")

    def test_interact_at_target_advances_to_talk_maya(self):
        q = self._quest()
        q.on_position(11.0, 10.0)
        self.assertIsNotNone(q.on_interact(10.5, 10.5))
        self.assertEqual(q.stage_id, "talk_maya")
        self.assertIn("Talk to Maya", q.objective)

    def test_interact_during_find_hotel_is_noop(self):
        q = self._quest()
        self.assertIsNone(q.on_interact(10.5, 10.5))
        self.assertEqual(q.stage_id, "find_hotel")

    def test_interact_at_target_completes_mission(self):
        q = self._quest()
        q.on_position(11.0, 10.0)
        q.on_interact(10.5, 10.5)
        self.assertIsNotNone(q.on_interact(10.5, 10.5))
        self.assertTrue(q.is_complete())
        self.assertEqual(q.objective, FIND_MAYA["complete_text"])

    def test_interact_after_complete_is_noop(self):
        q = self._quest()
        q.on_position(11.0, 10.0)
        q.on_interact(10.5, 10.5)
        q.on_interact(10.5, 10.5)
        self.assertIsNone(q.on_interact(10.5, 10.5))

    def test_position_after_complete_is_noop(self):
        q = self._quest()
        q.on_position(11.0, 10.0)
        q.on_interact(10.5, 10.5)
        q.on_interact(10.5, 10.5)
        self.assertIsNone(q.on_position(10.5, 10.5))


class TestCompass(unittest.TestCase):
    def test_eight_wind_labels(self):
        cases = {
            (1, 0): "E", (1, 1): "SE", (0, 1): "S", (-1, 1): "SW",
            (-1, 0): "W", (-1, -1): "NW", (0, -1): "N", (1, -1): "NE",
        }
        for (dx, dy), want in cases.items():
            self.assertEqual(direction_label(dx, dy), want, (dx, dy))

    def test_hint_direction_and_blocks(self):
        q = Quest(FIND_MAYA, (10.0, 10.0))
        self.assertEqual(q.compass_hint(10.0, 0.0), ("S", 1))
        self.assertEqual(q.compass_hint(0.0, 10.0), ("E", 1))
        self.assertEqual(q.compass_hint(10.0, 20.0), ("N", 1))
        self.assertEqual(q.compass_hint(38.0, 10.0), ("W", 2))

    def test_hint_here_when_adjacent(self):
        q = Quest(FIND_MAYA, (10.0, 10.0))
        self.assertEqual(q.compass_hint(10.2, 10.1), ("here", 0))

    def test_hint_none_when_complete(self):
        q = Quest(FIND_MAYA, (10.0, 10.0))
        q.on_position(11.0, 10.0)
        q.on_interact(10.5, 10.5)
        q.on_interact(10.5, 10.5)
        self.assertIsNone(q.compass_hint(0.0, 0.0))


class TestClockAndDeadline(unittest.TestCase):
    def test_clock_starts_at_ten_pm(self):
        q = Quest(FIND_MAYA, (0.0, 0.0))
        self.assertEqual(q.clock_text(), "22:00")

    def test_tick_advances_minutes(self):
        q = Quest(FIND_MAYA, (0.0, 0.0))
        q.tick(300.0)   # 300 s * 0.2 min/s = 60 in-game minutes
        self.assertEqual(q.clock_text(), "23:00")

    def test_tick_ignores_nonpositive_dt(self):
        q = Quest(FIND_MAYA, (0.0, 0.0))
        before = q.minutes_of_day
        self.assertIsNone(q.tick(0.0))
        self.assertIsNone(q.tick(-5.0))
        self.assertEqual(q.minutes_of_day, before)

    def test_completed_quest_stops_the_clock(self):
        q = Quest(FIND_MAYA, (0.0, 0.0))
        q.on_position(1.0, 0.0)
        q.on_interact(0.5, 0.0)
        q.on_interact(0.5, 0.0)
        self.assertTrue(q.is_complete())
        before = q.minutes_of_day
        self.assertIsNone(q.tick(1000.0))
        self.assertEqual(q.minutes_of_day, before)

    def test_past_deadline_soft_fails_and_resets(self):
        q = Quest(FIND_MAYA, (0.0, 0.0), start_hour=1, deadline_hour=2)
        q.stage_index = 1          # simulate mid-mission progress
        msg = q.tick(300.0)        # 300 s * 0.2 = 60 min -> exactly 2:00
        self.assertIsNotNone(msg)
        self.assertEqual(q.stage_index, 0)      # retry from finding the hotel
        self.assertEqual(q.clock_text(), "01:00")
        self.assertFalse(q.is_complete())

    def test_before_deadline_no_fail(self):
        q = Quest(FIND_MAYA, (0.0, 0.0), start_hour=1, deadline_hour=2)
        self.assertIsNone(q.tick(299.0))
        self.assertEqual(q.stage_index, 0)


class TestReward(unittest.TestCase):
    def test_collect_reward_returns_credits_once(self):
        q = Quest(FIND_MAYA, (10.0, 10.0))
        q.on_position(11.0, 10.0)
        q.on_interact(10.5, 10.5)
        q.on_interact(10.5, 10.5)
        self.assertTrue(q.is_complete())
        self.assertEqual(q.collect_reward(), config.MISSION_REWARD)
        self.assertEqual(q.collect_reward(), 0)

    def test_no_reward_before_completion(self):
        q = Quest(FIND_MAYA, (10.0, 10.0))
        self.assertEqual(q.collect_reward(), 0)
        q.on_position(11.0, 10.0)
        self.assertEqual(q.collect_reward(), 0)

    def test_reward_composes_with_survival_credits(self):
        n = Needs(credits=10)
        q = Quest(FIND_MAYA, (10.0, 10.0))
        q.on_position(10.0, 10.0)
        q.on_interact(10.0, 10.0)
        q.on_interact(10.0, 10.0)
        n.credits += q.collect_reward()
        self.assertEqual(n.credits, 10 + config.MISSION_REWARD)


class TestCityIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = gen.generate(seed=20260913)
        cls.grid = cls.city.grid

    def test_rooftop_entrance_present_and_walkable(self):
        r = self.city.rooftop
        self.assertIsNotNone(r)
        rx, ry = r
        self.assertTrue(self.grid.in_bounds(rx, ry))
        self.assertFalse(self.grid.is_solid(rx, ry))
        self.assertEqual(self.grid.type_of(rx, ry), ROOFTOP)

    def test_rooftop_is_at_the_hotel(self):
        rx, ry = self.city.rooftop
        lx, ly = self.city.landmark
        self.assertLess(math.hypot(rx - lx, ry - ly), 10.0)

    def test_rooftop_is_reachable_from_spawn(self):
        seen = _reachable(self.grid, self.city.spawn)
        self.assertIn(self.city.rooftop, seen)

    def test_mission_is_completable_in_generated_city(self):
        rx, ry = self.city.rooftop
        px, py = rx + 0.5, ry + 0.5
        q = Quest(FIND_MAYA, (rx, ry))
        self.assertIsNotNone(q.on_position(px, py))   # find the hotel
        self.assertEqual(q.stage_id, "reach_rooftop")
        self.assertIsNotNone(q.on_interact(px, py))   # ride to the rooftop
        self.assertEqual(q.stage_id, "talk_maya")
        self.assertIsNotNone(q.on_interact(px, py))   # talk to Maya
        self.assertTrue(q.is_complete())
        self.assertEqual(q.collect_reward(), config.MISSION_REWARD)

    def test_spawn_is_not_already_at_the_hotel(self):
        # the mission must ask the player to walk, not complete instantly
        q = Quest(FIND_MAYA, self.city.rooftop)
        sx, sy = self.city.spawn[0], self.city.spawn[1]
        self.assertIsNone(q.on_position(sx, sy))
        self.assertEqual(q.stage_id, "find_hotel")


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_advance_identically(self):
        a = Quest(FIND_MAYA, (10.0, 10.0))
        b = Quest(FIND_MAYA, (10.0, 10.0))
        steps = [(0.0, 0.0, False), (9.0, 9.0, False),
                 (10.0, 10.0, True), (10.0, 10.0, True)]
        for x, y, inter in steps:
            if inter:
                a.on_interact(x, y)
                b.on_interact(x, y)
            else:
                a.on_position(x, y)
                b.on_position(x, y)
        self.assertEqual(a.stage_index, b.stage_index)
        self.assertEqual(a.completed, b.completed)
        self.assertEqual(a.objective, b.objective)
        self.assertEqual(a.collect_reward(), b.collect_reward())


if __name__ == "__main__":
    unittest.main()
