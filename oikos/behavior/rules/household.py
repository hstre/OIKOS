"""Rule-based household budget decision (energy first, then goods).

Energy is treated as a basic need with low short-run price elasticity:
demand relative to need falls with the ratio of the current price to an
adaptive reference price, but not below a minimum share. Goods spending
follows a linear consumption function out of disposable income (after
energy) and pre-income wealth.
"""

from __future__ import annotations

import numpy as np

from ..protocol import ActionSpace, Box, DecisionBatch, ModelMeta, ObservationBatch


class HouseholdBudgetRule:
    def __init__(self, min_energy_share: float):
        self.min_energy_share = float(min_energy_share)
        self.meta = ModelMeta(
            name="household_budget_rule",
            version="0.1.0",
            kind="rule",
            deterministic=True,
            params={"min_energy_share": self.min_energy_share},
        )

    @staticmethod
    def action_space(obs: ObservationBatch) -> ActionSpace:
        return {
            "energy_wanted": Box(0.0, obs["need_kwh"]),
            "energy_kwh": Box(0.0, obs["need_kwh"]),
            "goods_budget": Box(0.0, obs["deposits"].astype(float)),
        }

    def decide(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        need = obs["need_kwh"]
        price = obs["energy_price"]
        ratio = price / obs["reference_price"]
        share = np.clip(ratio ** obs["elasticity"], self.min_energy_share, 1.0)
        wanted = need * share

        deposits = obs["deposits"].astype(float)
        affordable = np.floor(deposits) / price
        energy = np.minimum(wanted, affordable)
        energy_cost = energy * price

        remaining = np.maximum(0.0, deposits - np.ceil(energy_cost))
        budget = (
            obs["c_income"] * np.maximum(0.0, obs["net_income"] - energy_cost)
            + obs["c_wealth"] * np.maximum(0.0, obs["wealth_before_income"])
        )
        return {
            "energy_wanted": wanted,
            "energy_kwh": energy,
            "goods_budget": np.minimum(budget, remaining),
        }
