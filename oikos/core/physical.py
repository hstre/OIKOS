"""Physical stock-flow accounts (energy in kWh, goods in units).

Physical quantities are floats; balances are checked with a relative
tolerance, unlike monetary balances which are exact.
"""

from __future__ import annotations

from collections import defaultdict

from .ledger import InvariantViolation


class PhysicalAccounts:
    def __init__(self, rel_tol: float = 1e-9):
        self.rel_tol = rel_tol
        self.begin_period(0, goods_inventory=0.0)

    def begin_period(self, t: int, goods_inventory: float) -> None:
        self.t = t
        self.q: dict[str, float] = defaultdict(float)
        self.goods_inventory_start = goods_inventory

    def add(self, key: str, amount: float) -> None:
        self.q[key] += float(amount)

    def check(self, goods_inventory_end: float) -> None:
        q = self.q
        errors = []
        energy_in = q["energy_imported"]
        energy_out = q["energy_used_households"] + q["energy_used_firms"]
        if abs(energy_in - energy_out) > self.rel_tol * max(1.0, energy_in):
            errors.append(f"energy: imported {energy_in} != used {energy_out}")
        d_inv = goods_inventory_end - self.goods_inventory_start
        flows = q["goods_produced"] - q["goods_sold"] - q["goods_depreciated"] - q["goods_written_off"]
        if abs(d_inv - flows) > self.rel_tol * max(1.0, q["goods_produced"], goods_inventory_end):
            errors.append(f"goods: inventory change {d_inv} != net flows {flows}")
        if errors:
            raise InvariantViolation(f"t={self.t}: " + "; ".join(errors))
