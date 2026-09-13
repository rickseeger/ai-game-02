"""Interaction system (DESIGN 5.2): gates eat/drink to valid vendor locations.

A vendor is any restaurant the generator placed (DESIGN 5.5). Its *serving
footprint* is the sidewalk frontage the player actually stands at -- the awning,
tables, and chairs -- not the solid storefront wall behind them. An action is
legal when the player is within ``INTERACT_RANGE`` cells of one of those cells,
which is exactly "stopping to eat/drink at a restaurant".
"""
from .. import config


class Interactor:
    def __init__(self, grid, restaurants):
        self.grid = grid
        self.restaurants = list(restaurants)
        self.vendor_cells = self._serving_footprint(self.restaurants)

    @staticmethod
    def _serving_footprint(restaurants):
        cells = set()
        for r in restaurants:
            cells.update(r.tables)
            cells.update(r.chairs)
            cells.update(r.awning)
        return cells

    def nearest_vendor(self, x, y):
        """Return the nearest serving cell within ``INTERACT_RANGE``, else None."""
        r2 = config.INTERACT_RANGE * config.INTERACT_RANGE
        best = None
        best_d2 = r2
        for (vx, vy) in self.vendor_cells:
            dx = x - (vx + 0.5)
            dy = y - (vy + 0.5)
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = (vx, vy)
        return best

    def at_vendor(self, x, y):
        return self.nearest_vendor(x, y) is not None

    def try_eat(self, needs, x, y):
        if not self.at_vendor(x, y):
            needs.set_message("find a restaurant to eat")
            return False
        return needs.eat()

    def try_drink(self, needs, x, y):
        if not self.at_vendor(x, y):
            needs.set_message("find a vendor to buy a drink")
            return False
        return needs.drink()
