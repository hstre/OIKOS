"""Policy responses to an energy price shock.

All instruments get the same gross budget B, defined before the shock and
identically for every scenario of a seed:

    B = budget_share * (retail price increase per kWh) * (household energy
        use in the last pre-shock month) * duration

i.e. the share of the households' direct additional energy bill that the
state is prepared to cover, assuming unchanged quantities. Actual costs of
the subsidy are endogenous and reported separately.

Instruments
- none:        no response
- transfer:    equal lump-sum payment per household per month
- subsidy:     the state pays `budget_share` of the increase of the
               household retail price above its pre-shock level
- investment:  the state buys goods worth B/duration per month and turns
               them into retrofits that lower the energy need of the most
               energy-intensive households after a lag
"""

from __future__ import annotations

import numpy as np

INSTRUMENTS = ("none", "transfer", "subsidy", "investment")


class EnergyPolicy:
    def __init__(self, cfg: dict, n_households: int):
        self.instrument = cfg["instrument"]
        if self.instrument not in INSTRUMENTS:
            raise ValueError(f"unknown instrument {self.instrument!r}")
        self.budget_share = float(cfg["budget_share"])
        self.start = int(cfg["start_month"])
        self.duration = int(cfg["duration_months"])
        inv = cfg["investment"]
        self.cost_per_retrofit = float(inv["cost_per_retrofit_eur"]) * 100
        self.need_reduction = float(inv["need_reduction"])
        self.lag = int(inv["lag_months"])
        self.n_households = n_households
        self.budget: int | None = None
        self.base_price: np.ndarray | None = None
        self._retrofit_value = 0.0  # cents of goods bought, not yet turned into retrofits

    def active(self, t: int) -> bool:
        return self.start <= t < self.start + self.duration

    def fix_budget(self, price_increase_per_kwh: float, household_kwh: float,
                   base_household_price: np.ndarray) -> None:
        """Called once at the start month, before any instrument is used."""
        self.budget = int(self.budget_share * price_increase_per_kwh * household_kwh * self.duration)
        self.base_price = base_household_price.copy()

    # -- transfer
    def transfer_per_household(self, t: int) -> int:
        if self.instrument != "transfer" or not self.active(t):
            return 0
        return self.budget // (self.duration * self.n_households)

    # -- subsidy
    def household_price(self, supplier_price: np.ndarray, t: int) -> np.ndarray:
        if self.instrument != "subsidy" or not self.active(t):
            return supplier_price
        excess = np.maximum(0.0, supplier_price - self.base_price)
        return supplier_price - self.budget_share * excess

    # -- investment
    def investment_budget(self, t: int) -> int:
        if self.instrument != "investment" or not self.active(t):
            return 0
        return self.budget // self.duration

    def retrofits_from(self, value_bought: float) -> int:
        self._retrofit_value += value_bought
        n = int(self._retrofit_value // self.cost_per_retrofit)
        self._retrofit_value -= n * self.cost_per_retrofit
        return n
