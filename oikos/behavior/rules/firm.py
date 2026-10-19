"""Rule-based production, pricing and wage decisions of goods firms.

Adapted from the baseline model of Lengnick (2013): firms form adaptive
sales expectations, plan output to close a share of the gap to a target
inventory each month, adjust the markup when inventories leave a band,
and raise wages after unfilled vacancies (lower them after a long period
in which all vacancies were filled).
"""

from __future__ import annotations

import numpy as np

from ..protocol import ActionSpace, Box, DecisionBatch, ModelMeta, ObservationBatch


class FirmPlanningRule:
    def __init__(self, cfg: dict):
        self.expectation_weight = float(cfg["expectation_weight"])
        self.inventory_target = float(cfg["inventory_target"])
        self.inventory_adjustment = float(cfg["inventory_adjustment"])
        self.band_low, self.band_high = (float(x) for x in cfg["inventory_band"])
        self.markup_step = float(cfg["markup_step"])
        self.markup_min, self.markup_max = (float(x) for x in cfg["markup_bounds"])
        self.wage_step = float(cfg["wage_step"])
        self.wage_rigidity_months = int(cfg["wage_rigidity_months"])
        self.meta = ModelMeta(
            name="firm_planning_rule",
            version="0.1.0",
            kind="rule",
            deterministic=False,
            params={
                "expectation_weight": self.expectation_weight,
                "inventory_target": self.inventory_target,
                "inventory_adjustment": self.inventory_adjustment,
                "markup_step": self.markup_step,
                "wage_step": self.wage_step,
            },
        )

    def action_space(self, obs: ObservationBatch) -> ActionSpace:
        n = len(obs["inventory"])
        return {
            "expected_sales": Box(0.0, np.inf),
            "target_workers": Box(0.0, np.full(n, np.inf)),
            "markup": Box(self.markup_min, self.markup_max),
            "wage": Box(1.0, np.inf),
        }

    def decide(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        n = len(obs["inventory"])
        lam = self.expectation_weight
        expected = (1 - lam) * obs["expected_sales"] + lam * obs["last_sales"]
        gap = expected * self.inventory_target - obs["inventory"]
        desired_output = np.maximum(0.0, expected + self.inventory_adjustment * gap)
        target = np.ceil(desired_output / obs["productivity"])

        inv_ratio = obs["inventory"] / np.maximum(expected, 1e-9)
        u = rng.uniform(0.0, self.markup_step, n)
        factor = np.where(inv_ratio < self.band_low, 1 + u, np.where(inv_ratio > self.band_high, 1 - u, 1.0))
        markup = np.clip((1 + obs["markup"]) * factor - 1, self.markup_min, self.markup_max)

        uw = rng.uniform(0.0, self.wage_step, n)
        wage = obs["wage"].astype(float)
        wage = np.where(obs["unfilled_vacancies"] > 0, wage * (1 + uw), wage)
        wage = np.where(obs["months_all_filled"] >= self.wage_rigidity_months, wage * (1 - uw), wage)
        return {"expected_sales": expected, "target_workers": target, "markup": markup, "wage": wage}


class EnergySupplierRule:
    """Energy suppliers: adaptive sales expectation and staffing in
    proportion to expected sales. Prices are cost-plus with a fixed markup."""

    def __init__(self, cfg: dict):
        self.expectation_weight = float(cfg["expectation_weight"])
        self.labor_per_kwh = float(cfg["labor_per_kwh"])
        self.meta = ModelMeta(
            name="energy_supplier_rule", version="0.1.0", kind="rule", deterministic=True,
            params={"expectation_weight": self.expectation_weight},
        )

    @staticmethod
    def action_space(obs: ObservationBatch) -> ActionSpace:
        return {"expected_sales": Box(0.0, np.inf), "target_workers": Box(0.0, np.inf)}

    def decide(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        lam = self.expectation_weight
        expected = (1 - lam) * obs["expected_sales"] + lam * obs["last_sales"]
        return {"expected_sales": expected, "target_workers": np.ceil(expected * self.labor_per_kwh)}
