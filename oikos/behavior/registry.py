"""Build decision models from the `behavior` section of a configuration."""

from __future__ import annotations

from .rules.household import HouseholdBudgetRule


def build_household_model(cfg: dict):
    spec = cfg["behavior"]["household"]
    kind = spec["model"]
    if kind == "rule":
        return HouseholdBudgetRule(cfg["households"]["min_energy_share"])
    if kind == "llm_table":
        from .llm.household_table import TableHouseholdModel

        return TableHouseholdModel(spec["table"])
    raise ValueError(f"unknown household model {kind!r}")
