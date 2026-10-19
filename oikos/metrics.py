"""Per-period indicators. Everything reported here is computed from the
simulation state; nothing is estimated or smoothed."""

from __future__ import annotations

import numpy as np

ENERGY_BURDEN_THRESHOLD = 0.10  # energy spending above 10 % of net income


def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    if x.size == 0:
        return float("nan")
    x = x - min(0.0, x[0])  # shift if negative values occur
    total = x.sum()
    if total <= 0:
        return 0.0
    n = x.size
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * total))


def hhi(values: np.ndarray) -> float:
    total = values.sum()
    if total <= 0:
        return float("nan")
    s = values / total
    return float((s ** 2).sum())


def quintiles(income: np.ndarray) -> np.ndarray:
    """Quintile 0 (lowest) .. 4 (highest); ties broken by index for determinism."""
    order = np.argsort(income, kind="stable")
    q = np.empty(income.size, dtype=np.int64)
    q[order] = (np.arange(income.size) * 5) // income.size
    return q


def period_record(eco, *, t, p_world, p_hh, e_kwh, e_pay, forced, need, net_income, goods_hh, spend_hh,
                  sold, revenue, e_firms_kwh, imports_kwh, exits, policy_cost) -> dict:
    L, lay, H, F = eco.ledger, eco.layout, eco.H, eco.F
    employed = int((eco.employer >= 0).sum())
    price_index = float((eco.price * sold).sum() / sold.sum()) if sold.sum() > 0 else float(eco.price.mean())
    inc = np.maximum(net_income, 1)
    burden = e_pay / inc
    poor = burden > ENERGY_BURDEN_THRESHOLD
    rec = {
        "t": t,
        "world_price_ct_kwh": p_world,
        "hh_energy_price_ct_kwh": float(p_hh.mean()),
        "price_index": price_index,
        "avg_wage": float(eco.avg_wage),
        "unemployment": 1 - employed / H,
        "real_consumption": float(goods_hh.sum()),
        "nominal_consumption": float(spend_hh.sum()),
        "hh_energy_kwh": float(e_kwh.sum()),
        "firm_energy_kwh": e_firms_kwh,
        "energy_imports_kwh": imports_kwh,
        "energy_need_kwh": float(need.sum()),
        "energy_burden_share": float(poor.mean()),
        "energy_forced_shortfall_share": float(forced.mean()),
        "gini_net_income": gini(net_income),
        "gini_deposits": gini(L.deposits[:H]),
        "hhi_goods": hhi(sold),
        "firm_exits": exits,
        "markup_mean": float(eco.markup.mean()),
        "inventory": float(eco.inventory.sum()),
        "gov_debt": int(L.loans[lay.government] - L.deposits[lay.government]),
        "gov_purchases": eco._period["gov_purchases"],
        "taxes": eco._period["taxes"],
        "policy_cost": policy_cost,
        "transfers": eco._period["transfers"],
        "subsidy": eco._period["subsidy"],
        "investment": eco._period["investment"],
        "exports": eco._period["exports"],
        "retrofits_cum": eco.cum["retrofits"],
        "bank_equity": int(L.bank_equity),
        "bank_write_offs": int(L.write_offs),
        "private_loans": int(L.loans[eco.producers].sum()),
        "money_stock": L.money_stock(),
        "money_created": L.money_created,
        "money_destroyed": L.money_destroyed,
        "row_deposits": int(L.deposits[lay.rest_of_world]),
    }
    for q in range(5):
        m = eco.quintile == q
        rec[f"q{q + 1}_real_consumption"] = float(goods_hh[m].mean())
        rec[f"q{q + 1}_energy_burden_share"] = float(poor[m].mean())
        rec[f"q{q + 1}_net_income"] = float(net_income[m].mean())
    return rec
