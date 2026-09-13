"""Light survival loop tests (node 5): decay/replenish math, clamping,
the credit + free-sample economy, and the gentle non-lethal health drain.

Mirrors DESIGN 7.2: 1 point / 60 s decay, eat (+35 hunger) / drink (+30
thirst), a hint at <= 20, slow health drain at 0, and a health floor with no
death by starvation.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from citywalk import config
from citywalk.world.survival import Needs


class TestDecay(unittest.TestCase):
    def test_decay_rate_is_one_point_per_minute(self):
        n = Needs()
        n.tick(60.0)
        self.assertAlmostEqual(n.hunger, 100.0 - 1.0, places=6)
        self.assertAlmostEqual(n.thirst, 100.0 - 1.0, places=6)

    def test_decay_is_slow_not_punishing(self):
        n = Needs()
        n.tick(60.0 * 10.0)   # ten minutes
        self.assertGreater(n.hunger, 85.0)
        self.assertGreater(n.thirst, 85.0)

    def test_decay_clamps_at_zero(self):
        n = Needs(hunger=0.5, thirst=0.5)
        n.tick(3600.0)
        self.assertEqual(n.hunger, 0.0)
        self.assertEqual(n.thirst, 0.0)

    def test_tick_ignores_nonpositive_dt(self):
        n = Needs()
        n.tick(0.0)
        n.tick(-5.0)
        self.assertEqual(n.hunger, 100.0)
        self.assertEqual(n.thirst, 100.0)


class TestReplenish(unittest.TestCase):
    def test_eat_restores_hunger(self):
        n = Needs(hunger=50.0)
        self.assertTrue(n.eat())
        self.assertAlmostEqual(n.hunger, 50.0 + config.MEAL_HUNGER, places=6)
        self.assertEqual(n.thirst, 100.0)   # unaffected

    def test_drink_restores_thirst(self):
        n = Needs(thirst=40.0)
        self.assertTrue(n.drink())
        self.assertAlmostEqual(n.thirst, 40.0 + config.DRINK_THIRST, places=6)
        self.assertEqual(n.hunger, 100.0)

    def test_replenish_clamps_to_full(self):
        n = Needs(hunger=90.0)
        self.assertTrue(n.eat())
        self.assertEqual(n.hunger, 100.0)

    def test_eat_when_full_is_refused_without_cost(self):
        n = Needs(hunger=100.0, credits=40)
        self.assertFalse(n.eat())
        self.assertEqual(n.hunger, 100.0)
        self.assertEqual(n.credits, 40)
        self.assertEqual(n.message, "already full")


class TestEconomy(unittest.TestCase):
    def test_eat_and_drink_cost_credits(self):
        n = Needs(credits=40, hunger=50.0, thirst=50.0)
        self.assertTrue(n.eat())
        self.assertEqual(n.credits, 40 - config.MEAL_COST)
        self.assertTrue(n.drink())
        self.assertEqual(n.credits, 40 - config.MEAL_COST - config.DRINK_COST)

    def test_free_samples_cover_insufficient_credits(self):
        n = Needs(credits=0, free_samples=2, hunger=50.0)
        self.assertTrue(n.eat())
        self.assertEqual(n.credits, 0)
        self.assertEqual(n.free_samples, 1)
        self.assertGreater(n.hunger, 50.0)

    def test_no_credits_and_no_samples_refuses(self):
        n = Needs(credits=0, free_samples=0, hunger=50.0)
        self.assertFalse(n.eat())
        self.assertEqual(n.hunger, 50.0)
        self.assertEqual(n.message, "not enough credits")


class TestConsequences(unittest.TestCase):
    def test_low_hint_between_zero_and_low_threshold(self):
        self.assertTrue(Needs(hunger=config.NEED_LOW).is_low())
        self.assertTrue(Needs(thirst=config.NEED_LOW - 0.1).is_low())
        self.assertFalse(Needs(hunger=config.NEED_LOW + 0.1).is_low())
        self.assertFalse(Needs(hunger=0.0).is_low())   # starving, not just low

    def test_starving_when_either_meter_is_empty(self):
        self.assertTrue(Needs(hunger=0.0).is_starving())
        self.assertTrue(Needs(thirst=0.0).is_starving())
        self.assertFalse(Needs(hunger=1.0, thirst=1.0).is_starving())

    def test_health_drains_slowly_while_starving(self):
        n = Needs(hunger=0.0, health=100.0)
        n.tick(10.0)
        self.assertAlmostEqual(n.health, 100.0 - 1.0, places=6)

    def test_health_never_drops_below_floor(self):
        n = Needs(hunger=0.0, health=100.0)
        n.tick(3600.0 * 24.0)   # a full day of starvation
        self.assertEqual(n.health, config.HEALTH_FLOOR)
        self.assertGreater(n.health, 0.0)   # no death by starvation

    def test_health_does_not_drain_when_fed(self):
        n = Needs(hunger=50.0, thirst=50.0, health=100.0)
        n.tick(120.0)
        self.assertEqual(n.health, 100.0)


class TestDeterminism(unittest.TestCase):
    def test_same_tick_sequence_is_reproducible(self):
        a = Needs()
        b = Needs()
        dts = [1.0 / 30.0] * 90
        for dt in dts:
            a.tick(dt)
            b.tick(dt)
        self.assertEqual(a.hunger, b.hunger)
        self.assertEqual(a.thirst, b.thirst)
        self.assertEqual(a.health, b.health)

    def test_message_expires(self):
        n = Needs()
        n.set_message("ate a meal")
        self.assertTrue(n.message)
        n.tick(config.MESSAGE_TTL + 0.01)
        self.assertEqual(n.message, "")


if __name__ == "__main__":
    unittest.main()
