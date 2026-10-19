"""Scalar indicators per run. Windows (months relative to shock start):
pre = -12..-1, shock = 0..23, after = 24..59."""

from __future__ import annotations

import numpy as np
import pandas as pd

PRE = (-12, 0)
SHOCK = (0, 24)
AFTER = (24, 60)

# name -> (description, unit) ; used by the report
INDICATORS = {
    "unemployment_shock": ("Arbeitslosenquote, Mittel Monate 0–23", "Anteil"),
    "unemployment_after": ("Arbeitslosenquote, Mittel Monate 24–59", "Anteil"),
    "unemployment_peak": ("Arbeitslosenquote, Maximum Monate 0–59", "Anteil"),
    "recovery_months": ("Monate bis Arbeitslosigkeit wieder ≤ Vorkrisenniveau + 1 Pp.", "Monate"),
    "real_consumption_shock": ("Realer Konsum aller Haushalte, Mittel 0–23", "Gütereinheiten/Monat"),
    "q1_real_consumption_shock": ("Realer Konsum unterstes Einkommensquintil, Mittel 0–23", "Einheiten/Haushalt"),
    "q5_real_consumption_shock": ("Realer Konsum oberstes Einkommensquintil, Mittel 0–23", "Einheiten/Haushalt"),
    "energy_burden_shock": ("Anteil Haushalte mit Energieausgaben > 10 % des Nettoeinkommens, 0–23", "Anteil"),
    "q1_energy_burden_shock": ("dto., unterstes Quintil", "Anteil"),
    "forced_shortfall_shock": ("Anteil Haushalte, die gewünschte Energie nicht bezahlen können, 0–23", "Anteil"),
    "energy_imports_shock": ("Importierte Primärenergie, Summe 0–23", "GWh"),
    "energy_imports_after": ("Importierte Primärenergie, Summe 24–59", "GWh"),
    "price_index_shock": ("Güterpreisindex 0–23 relativ zu Vorkrisenniveau", "Faktor"),
    "gini_income_shock": ("Gini verfügbares Einkommen, Mittel 0–23", "Index"),
    "gini_deposits_end": ("Gini Einlagen (ohne Unternehmensbeteiligungen), Monat 59", "Index"),
    "hhi_goods_shock": ("Herfindahl-Index Gütermarkt, Mittel 0–23", "Index"),
    "firm_exits": ("Firmenaustritte 0–59", "Anzahl"),
    "bank_write_offs": ("Kreditabschreibungen der Bank 0–59", "Mio. €"),
    "gov_debt_change": ("Veränderung Staatsschuld (netto) Monat −1 bis 59", "Mio. €"),
    "policy_cost": ("Tatsächliche Programmkosten 0–59", "Mio. €"),
}


def _win(df: pd.DataFrame, w: tuple[int, int]) -> pd.DataFrame:
    return df[(df.t >= w[0]) & (df.t < w[1])]


def summarize_run(df: pd.DataFrame, info: dict) -> dict:
    pre, shock, after = _win(df, PRE), _win(df, SHOCK), _win(df, AFTER)
    post = _win(df, (0, 60))
    u_pre = pre.unemployment.mean()
    rec_idx = np.nonzero(post.unemployment.to_numpy() <= u_pre + 0.01)[0]
    peak_pos = int(np.argmax(post.unemployment.to_numpy()))
    later = rec_idx[rec_idx >= peak_pos]
    debt_before = df.loc[df.t == -1, "gov_debt"].iloc[0]
    return {
        "scenario": info["scenario"],
        "seed": info["seed"],
        "budget": info["budget"] / 1e8 if info["budget"] is not None else np.nan,
        "unemployment_shock": shock.unemployment.mean(),
        "unemployment_after": after.unemployment.mean(),
        "unemployment_peak": post.unemployment.max(),
        "recovery_months": float(later[0]) if later.size else float(len(post)),
        "real_consumption_shock": shock.real_consumption.mean(),
        "q1_real_consumption_shock": shock.q1_real_consumption.mean(),
        "q5_real_consumption_shock": shock.q5_real_consumption.mean(),
        "energy_burden_shock": shock.energy_burden_share.mean(),
        "q1_energy_burden_shock": shock.q1_energy_burden_share.mean(),
        "forced_shortfall_shock": shock.energy_forced_shortfall_share.mean(),
        "energy_imports_shock": shock.energy_imports_kwh.sum() / 1e6,
        "energy_imports_after": after.energy_imports_kwh.sum() / 1e6,
        "price_index_shock": shock.price_index.mean() / pre.price_index.mean(),
        "gini_income_shock": shock.gini_net_income.mean(),
        "gini_deposits_end": post.gini_deposits.iloc[-1],
        "hhi_goods_shock": shock.hhi_goods.mean(),
        "firm_exits": int(post.firm_exits.sum()),
        "bank_write_offs": post.bank_write_offs.sum() / 1e8,
        "gov_debt_change": (post.gov_debt.iloc[-1] - debt_before) / 1e8,
        "policy_cost": post.policy_cost.sum() / 1e8,
        "retrofits": int(post.retrofits_cum.iloc[-1]),
    }
