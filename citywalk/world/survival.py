"""Light survival loop (DESIGN 7.2): slowly decaying hunger/thirst meters and
their gentle, non-lethal consequences.

Pure state + ``tick(dt)`` + ``eat()``/``drink()``. This module does no
rendering and performs no location gating -- ``world.interact`` decides whether
an eat/drink action is legal at the player's position; ``Needs`` only models
the meters, the health consequence, the tiny credit economy, and the transient
message the HUD reads.

Intentional lightness (DESIGN 7.2):

  * decay is 1 point / 60 real seconds, so a full bar lasts ~100 minutes --
    pacing, never pressure;
  * replenish only via eat/drink (location-gated elsewhere at vendors);
  * consequences are a gentle HUD hint at <= 20 and a slow health drain at 0;
  * health never falls below a non-lethal floor -- no death by starvation.
"""
from .. import config


class Needs:
    """Hunger/thirst/health/credits state plus the transient HUD message."""

    def __init__(self, hunger=None, thirst=None, health=None, credits=None,
                 free_samples=None):
        self.hunger = config.NEED_START if hunger is None else float(hunger)
        self.thirst = config.NEED_START if thirst is None else float(thirst)
        self.health = config.START_HEALTH if health is None else float(health)
        self.credits = config.START_CREDITS if credits is None else int(credits)
        self.free_samples = (config.FREE_SAMPLES if free_samples is None
                             else int(free_samples))
        self.message = ""
        self.last_action = ""
        self._message_ttl = 0.0

    # -- meter queries -----------------------------------------------------
    def is_starving(self):
        return self.hunger <= 0.0 or self.thirst <= 0.0

    def is_low(self):
        """True when a meter is low but not yet empty (the gentle HUD hint)."""
        return ((0.0 < self.hunger <= config.NEED_LOW)
                or (0.0 < self.thirst <= config.NEED_LOW))

    # -- simulation --------------------------------------------------------
    def tick(self, dt):
        """Advance decay and consequences by ``dt`` seconds."""
        if not (dt > 0.0):
            return
        self.hunger = max(0.0, self.hunger - config.NEED_DECAY_PER_SEC * dt)
        self.thirst = max(0.0, self.thirst - config.NEED_DECAY_PER_SEC * dt)
        if self.is_starving():
            self.health = max(config.HEALTH_FLOOR,
                              self.health - config.HEALTH_DRAIN_PER_SEC * dt)
        if self._message_ttl > 0.0:
            self._message_ttl -= dt
            if self._message_ttl <= 0.0:
                self.message = ""

    # -- actions (the caller MUST gate these by valid location) -------------
    def eat(self):
        return self._replenish("hunger", config.MEAL_HUNGER, config.MEAL_COST,
                               "ate a meal", "+%d hunger" % int(config.MEAL_HUNGER))

    def drink(self):
        return self._replenish("thirst", config.DRINK_THIRST, config.DRINK_COST,
                               "bought a drink", "+%d thirst" % int(config.DRINK_THIRST))

    def _replenish(self, attr, amount, cost, label, delta_text):
        current = getattr(self, attr)
        if current >= config.NEED_START:
            self.set_message("already full")
            return False
        if self.credits >= cost:
            self.credits -= cost
        elif self.free_samples > 0:
            self.free_samples -= 1
        else:
            self.set_message("not enough credits")
            return False
        setattr(self, attr, min(config.NEED_START, current + amount))
        self.last_action = label
        self.set_message("%s (%s)" % (label, delta_text))
        return True

    def set_message(self, text):
        self.message = text
        self._message_ttl = config.MESSAGE_TTL
