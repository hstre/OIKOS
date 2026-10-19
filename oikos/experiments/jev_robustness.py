"""Robustness tests for the Jev household budget question (observation only).

The 48 household states of the first observation run are put to Jev again,
each test changing exactly one factor of the request:

  T5_repeat          the unchanged original requests, asked again live
  T1_reversed_order  options listed in reverse order; same identifiers, amounts, texts
  T2_euro_only       option texts with euro amounts only, without percentages
  T3_with_history    plus last month's spending on other goods from the rule run,
                     labelled as synthetic model history
  T4_wider_range     a wider set of budgets including 30 % and 45 % of the income
                     left after the energy bill (other options unchanged)

The economy is not involved: states are reconstructed from a rule-only run
(seed 1) and checked byte for byte against the logged original requests.
Comparisons use euro budgets and full score distributions. Scores are
model-internal values, not empirical choice probabilities; agreement with
the rule is not a success criterion.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..behavior.jev.client import CallRecord, JevClient, ReplayClient, request_hash
from ..behavior.jev.household_budget import (DECISION_VERSION, PROBABILITY_SEMANTICS, JevBudgetObserver,
                                             build_request, parse_choice)
from ..model import Economy
from .jev_observe import load_spec
from .runner import _git

WIDE_FRACTIONS = [0.3, 0.45, 0.6, 0.75, 0.9, 1.0, 1.1]
HISTORY_FIELD = "spending_on_other_goods_and_services_last_month_eur"
HISTORY_NOTE = ("The last-month spending figure is synthetic history produced by the simulation model, "
                "not observed household data.")
TESTS = ["T5_repeat", "T1_reversed_order", "T2_euro_only", "T3_with_history", "T4_wider_range"]
MAX_PER_TEST = 50


# ------------------------------------------------------------ states
class _Recorder:
    """Records exact household values for the sampled households, using the
    same sampling stream and code as the observation run."""

    def __init__(self, months, per_month):
        self.months, self.per_month = set(months), per_month
        self.eco = None
        self.states: list[dict] = []

    def wants(self, t):
        return t in self.months

    def observe(self, t, obs, decision, rng):
        for i in JevBudgetObserver.sample(len(obs["deposits"]), self.per_month, rng):
            price = float(obs["energy_price"][i])
            self.states.append({
                "t": t, "household": int(i),
                "exact": {"employed": bool(obs["employed"][i]), "net_income": float(obs["net_income"][i]),
                          "savings": float(obs["wealth_before_income"][i]), "deposits": float(obs["deposits"][i]),
                          "price_now": price, "price_usual": float(obs["reference_price"][i]),
                          "energy_cost": float(decision["energy_kwh"][i]) * price},
                "prev_goods_spending_cents": float(self.eco.last_goods_spending[i]),
                "rule_budget_cents": float(decision["goods_budget"][i]),
            })


def reconstruct_states(spec_path, original_log) -> tuple[list[dict], dict]:
    spec, cfg = load_spec(spec_path)
    jev = spec["jev"]
    rec = _Recorder(jev["months"], int(jev["households_per_month"]))
    eco = Economy(cfg, int(spec["seed"]), models={"household_observer": rec})
    rec.eco = eco
    eco.run()
    original = [json.loads(x) for x in Path(original_log).read_text().splitlines() if x.strip()]
    if len(original) != len(rec.states):
        raise ValueError(f"{len(rec.states)} reconstructed states, {len(original)} in the original log")
    fractions = [float(f) for f in jev["budget_fractions"]]
    for st, row in zip(rec.states, original):
        body, options = build_request(jev["model"], fractions=fractions, **st["exact"])
        if (st["t"], st["household"]) != (row["t"], row["household"]) or request_hash(body) != row["request_sha256"]:
            raise ValueError(f"state t={st['t']} household={st['household']} differs from the original request")
        st["original"] = row
        st["options"] = options
    return rec.states, jev


# ----------------------------------------------------------- variants
def variant(test: str, st: dict, jev: dict) -> tuple[dict, dict[str, int]]:
    """Request body and option amounts (cents) for one test and state."""
    fractions = [float(f) for f in jev["budget_fractions"]]
    body, options = build_request(jev["model"], fractions=fractions, **st["exact"])
    q = body["questions"]["goods_budget"]
    if test == "T5_repeat":
        pass
    elif test == "T1_reversed_order":
        q["criteria"] = dict(reversed(list(q["criteria"].items())))
    elif test == "T2_euro_only":
        q["criteria"] = {k: f"Spend about {round(options[k] / 100)} €." for k in q["criteria"]}
    elif test == "T3_with_history":
        body["state"]["history_note"] = HISTORY_NOTE
        body["state"]["household"][HISTORY_FIELD] = int(round(st["prev_goods_spending_cents"] / 100))
    elif test == "T4_wider_range":
        body, options = build_request(jev["model"], fractions=WIDE_FRACTIONS, **st["exact"])
    else:
        raise ValueError(test)
    return body, options


# ------------------------------------------------------------- costs
class CostGuard:
    """Shared limit over all tests. A request is sent only if the money
    spent so far plus a reserve for this request stays within the limit."""

    def __init__(self, limit_usd: float):
        self.limit = float(limit_usd)
        self.spent = 0.0
        self.max_seen = 0.0

    def allow(self) -> bool:
        reserve = max(6e-5, 1.5 * self.max_seen)
        return self.spent + reserve <= self.limit

    def add(self, cost) -> None:
        c = float(cost or 0.0)
        self.spent += c
        self.max_seen = max(self.max_seen, c)


# --------------------------------------------------------------- run
def run_tests(spec_path, original_log, out_dir, cost_limit_usd: float = 0.01, client=None,
              mode: str = "live", replay_dir=None, tests=TESTS, log=print) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    states, jev = reconstruct_states(spec_path, original_log)
    if len(states) > MAX_PER_TEST:
        raise ValueError("more states than the per-test limit")
    if client is None:
        if mode == "live":
            client = JevClient(endpoint=jev["endpoint"], timeout=float(jev["timeout_s"]), retries=int(jev["retries"]))
        else:
            client = _MultiReplay([Path(replay_dir) / f"{t}.jsonl" for t in tests])
    guard = CostGuard(cost_limit_usd)
    results: dict[str, list[dict]] = {}
    for test in tests:
        rows = []
        for st in states:
            body, options = variant(test, st, jev)
            shown = list(body["questions"]["goods_budget"]["criteria"])
            row = {"type": "call", "test": test, "t": st["t"], "household": st["household"],
                   "decision": DECISION_VERSION, "probability_semantics": PROBABILITY_SEMANTICS,
                   "options_cents": options, "shown_order": shown,
                   "base_cents": max(0.0, st["exact"]["net_income"] - st["exact"]["energy_cost"]),
                   "rule_budget_cents": st["rule_budget_cents"]}
            if test == "T3_with_history":
                row["history_is_synthetic"] = True
            if mode == "live" and not guard.allow():
                row.update(status="skipped_cost_limit", request=body, request_sha256=request_hash(body))
                rows.append(row)
                continue
            rec: CallRecord = client.decide(body)
            guard.add(rec.cost_usd if not rec.replayed else 0.0)
            row.update(rec.to_dict())
            if rec.status == "ok":
                try:
                    choice, probs, conf = parse_choice(rec.response, list(options))
                    row.update(jev_choice=choice, jev_position=shown.index(choice) + 1, jev_scores=probs,
                               jev_confidence=conf, jev_budget_cents=options[choice])
                except Exception as e:  # noqa: BLE001 - recorded, never replaced
                    row.update(status="error", error_kind=getattr(e, "kind", "error"), error=str(e)[:300])
            rows.append(row)
        with open(out / f"{test}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        results[test] = rows
        log(f"{test}: {sum(r['status'] == 'ok' for r in rows)}/{len(rows)} ok")
    summary = analyse(states, results, guard, mode, cost_limit_usd)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(summary, out / "report.md")
    return summary


class _MultiReplay(ReplayClient):
    def __init__(self, paths):
        self.records = {}
        for p in paths:
            if Path(p).exists():
                self.records.update(ReplayClient(p).records)


# ---------------------------------------------------------- analysis
def _tvd(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def _weighted(scores: dict, options: dict) -> float:
    return sum(scores[k] * options[k] for k in scores)


def _q(x, q):
    return float(np.quantile(x, q)) if len(x) else None


def _share_bins(scores: dict, options: dict, base: float) -> dict:
    """Score mass by budget as share of the income left after the energy bill."""
    out = {"<55%": 0.0, "55-65%": 0.0, "65-80%": 0.0, "80-95%": 0.0, ">=95%": 0.0}
    for k, p in scores.items():
        s = options[k] / base if base > 0 else 0.0
        b = "<55%" if s < 0.55 else "55-65%" if s < 0.65 else "65-80%" if s < 0.80 else "80-95%" if s < 0.95 else ">=95%"
        out[b] += p
    return out


def analyse(states, results, guard, mode, limit) -> dict:
    orig = [{"choice": st["original"]["jev_choice"], "scores": st["original"]["jev_scores"],
             "options": st["original"]["options_cents"], "base": max(0.0, st["exact"]["net_income"] - st["exact"]["energy_cost"]),
             "t": st["t"], "employed": st["exact"]["employed"],
             "savings_months": st["exact"]["savings"] / max(st["exact"]["net_income"], 1.0)} for st in states]
    sav_median = float(np.median([o["savings_months"] for o in orig]))

    def describe(rows_parsed):
        ok = [r for r in rows_parsed if r is not None]
        shares = [_weighted(r["scores"], r["options"]) / r["base"] for r in ok if r["base"] > 0]
        chosen = [r["options"][r["choice"]] / r["base"] for r in ok if r["base"] > 0]
        mass = {k: float(np.mean([_share_bins(r["scores"], r["options"], r["base"])[k] for r in ok]))
                for k in ["<55%", "55-65%", "65-80%", "80-95%", ">=95%"]} if ok else {}

        def grp(pred):
            v = [_weighted(r["scores"], r["options"]) / r["base"] for r in ok if pred(r) and r["base"] > 0]
            return {"n": len(v), "mean_weighted_share": float(np.mean(v)) if v else None}

        return {
            "n_ok": len(ok),
            "chosen_share_of_base": {"median": _q(chosen, 0.5), "q10": _q(chosen, 0.1), "q90": _q(chosen, 0.9)},
            "score_weighted_share_of_base": {"median": _q(shares, 0.5), "q10": _q(shares, 0.1), "q90": _q(shares, 0.9)},
            "mean_score_mass_by_share": mass,
            "groups": {"before_or_after_shock": grp(lambda r: r["t"] in (-1, 30)),
                       "during_shock": grp(lambda r: r["t"] in (3, 12)),
                       "employed": grp(lambda r: r["employed"]),
                       "unemployed": grp(lambda r: not r["employed"]),
                       "savings_below_median": grp(lambda r: r["savings_months"] < sav_median),
                       "savings_above_median": grp(lambda r: r["savings_months"] >= sav_median)},
        }

    out = {"decision": DECISION_VERSION, "probability_semantics": PROBABILITY_SEMANTICS, "mode": mode,
           "cost_limit_usd": limit, "git_commit": _git("rev-parse", "HEAD"),
           "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
           "n_states": len(states), "original": describe(orig), "tests": {}}
    total_cost = 0.0
    for test, rows in results.items():
        parsed, tvds, same_amount, d_chosen_eur, d_weighted_eur = [], [], [], [], []
        positions, keys = {}, {}
        for r, o in zip(rows, orig):
            if r["status"] != "ok":
                parsed.append(None)
                continue
            p = {"choice": r["jev_choice"], "scores": r["jev_scores"], "options": r["options_cents"], "base": o["base"],
                 "t": o["t"], "employed": o["employed"], "savings_months": o["savings_months"]}
            parsed.append(p)
            keys[r["jev_choice"]] = keys.get(r["jev_choice"], 0) + 1
            positions[str(r["jev_position"])] = positions.get(str(r["jev_position"]), 0) + 1
            d_chosen_eur.append((r["options_cents"][r["jev_choice"]] - o["options"][o["choice"]]) / 100)
            d_weighted_eur.append((_weighted(r["jev_scores"], r["options_cents"]) - _weighted(o["scores"], o["options"])) / 100)
            same_amount.append(r["options_cents"][r["jev_choice"]] == o["options"][o["choice"]])
            if set(r["options_cents"]) == set(o["options"]) and all(r["options_cents"][k] == o["options"][k] for k in o["options"]):
                tvds.append(_tvd(r["jev_scores"], o["scores"]))
        costs = [r.get("cost_usd") for r in rows if isinstance(r.get("cost_usd"), (int, float))]
        total_cost += sum(costs) if mode == "live" else 0.0
        kinds = {}
        for r in rows:
            if r["status"] != "ok":
                k = r.get("error_kind") or r["status"]
                kinds[k] = kinds.get(k, 0) + 1
        out["tests"][test] = {
            "requests_sent": sum(r["status"] != "skipped_cost_limit" for r in rows),
            "skipped_cost_limit": sum(r["status"] == "skipped_cost_limit" for r in rows),
            "errors_by_kind": kinds,
            "models_served": sorted({r["model_served"] for r in rows if r.get("model_served")}),
            "cost_usd": round(sum(costs), 8) if costs else 0.0,
            "chosen_key_counts": dict(sorted(keys.items())),
            "chosen_position_counts": dict(sorted(positions.items())),
            "same_euro_budget_as_original_share": float(np.mean(same_amount)) if same_amount else None,
            "chosen_budget_diff_vs_original_eur": {"median": _q(d_chosen_eur, 0.5), "q10": _q(d_chosen_eur, 0.1),
                                                   "q90": _q(d_chosen_eur, 0.9)},
            "score_weighted_budget_diff_vs_original_eur": {"median": _q(d_weighted_eur, 0.5),
                                                           "q10": _q(d_weighted_eur, 0.1), "q90": _q(d_weighted_eur, 0.9)},
            "tvd_vs_original": {"n": len(tvds), "median": _q(tvds, 0.5), "q90": _q(tvds, 0.9),
                                "max": float(max(tvds)) if tvds else None},
            **describe(parsed),
        }
    out["cost_usd_total"] = round(total_cost, 8)
    return out


def _f(x, pct=False):
    if x is None:
        return "–"
    return f"{x:.0%}" if pct else (f"{x:.3f}" if abs(x) < 10 else f"{x:.0f}")


def write_report(s: dict, path: Path) -> None:
    o = s["original"]
    md = [f"# Jev-Robustheitstests: {s['decision']}", "",
          "Nur Beobachtung, dieselben 48 Haushaltszustände wie im ersten Lauf, je Test genau ein veränderter Faktor. "
          "Scores sind modellinterne Werte, keine empirischen Entscheidungswahrscheinlichkeiten. "
          "„Anteil“ = Budget relativ zum Einkommen nach der Energierechnung.", "",
          f"- Modus: {s['mode']}; Kosten gesamt {s['cost_usd_total']} USD (Limit {s['cost_limit_usd']} USD)",
          f"- Code: `{s['git_commit'][:12]}`" + (" (mit uncommitteten Änderungen)" if s["git_dirty"] else ""), "",
          "## Überblick", "",
          "| Test | gesendet | Fehler/übersprungen | gewählter Anteil Median (10–90 %) | score-gewichteter Anteil Median (10–90 %) | gleiches €-Budget wie Original | TVD zum Original Median / Max |",
          "|---|---|---|---|---|---|---|",
          f"| Original (Lauf 1) | 48 | – | {_f(o['chosen_share_of_base']['median'], 1)} ({_f(o['chosen_share_of_base']['q10'], 1)}–{_f(o['chosen_share_of_base']['q90'], 1)}) | "
          f"{_f(o['score_weighted_share_of_base']['median'], 1)} ({_f(o['score_weighted_share_of_base']['q10'], 1)}–{_f(o['score_weighted_share_of_base']['q90'], 1)}) | – | – |"]
    for t, r in s["tests"].items():
        c, w, tv = r["chosen_share_of_base"], r["score_weighted_share_of_base"], r["tvd_vs_original"]
        err = sum(r["errors_by_kind"].values())
        md.append(f"| {t} | {r['requests_sent']} | {err} {r['errors_by_kind'] or ''} | {_f(c['median'], 1)} ({_f(c['q10'], 1)}–{_f(c['q90'], 1)}) | "
                  f"{_f(w['median'], 1)} ({_f(w['q10'], 1)}–{_f(w['q90'], 1)}) | {_f(r['same_euro_budget_as_original_share'], 1)} | "
                  f"{_f(tv['median'])} / {_f(tv['max'])} |")
    md += ["", "TVD = Totalvariationsabstand der Score-Verteilungen über dieselben Optionen (0 = identisch, 1 = disjunkt); "
           "nur für Tests mit identischen Optionsbeträgen. T5 zeigt das Rauschen zwischen zwei Live-Abfragen.", "",
           "## Mittlere Score-Masse nach Budgetanteil", "",
           "| Test | <55 % | 55–65 % | 65–80 % | 80–95 % | ≥95 % |", "|---|---|---|---|---|---|"]
    rows = [("Original", o)] + list(s["tests"].items())
    for name, r in rows:
        m = r["mean_score_mass_by_share"]
        md.append(f"| {name} | " + " | ".join(_f(m.get(k), 1) for k in ["<55%", "55-65%", "65-80%", "80-95%", ">=95%"]) + " |")
    md += ["", "## Reihenfolge, Positionen und Kennungen", "",
           "| Test | gewählte Kennungen | gewählte Positionen (1 = zuerst gezeigt) |", "|---|---|---|"]
    for t, r in s["tests"].items():
        md.append(f"| {t} | {r['chosen_key_counts']} | {r['chosen_position_counts']} |")
    md += ["", "In T1 tragen b1…b5 weiterhin dieselben Beträge; nur die Reihenfolge ist umgekehrt (b5 steht an Position 1). "
           "Ein Einfluss der Kennungen selbst wird dadurch nicht ausgeschlossen.", "",
           "## Reaktion auf Informationen: mittlerer score-gewichteter Anteil nach Gruppen", "",
           "| Test | vor/nach Schock | im Schock | erwerbstätig | erwerbslos | Ersparnis < Median | ≥ Median |",
           "|---|---|---|---|---|---|---|"]
    for name, r in rows:
        g = r["groups"]
        md.append(f"| {name} | " + " | ".join(f"{_f(g[k]['mean_weighted_share'], 1)} (n={g[k]['n']})" for k in
                  ["before_or_after_shock", "during_shock", "employed", "unemployed", "savings_below_median", "savings_above_median"]) + " |")
    md += ["", "## Kosten und Modelle", "", "| Test | Kosten USD | Modelle |", "|---|---|---|"]
    md += [f"| {t} | {r['cost_usd']} | {', '.join(r['models_served'])} |" for t, r in s["tests"].items()]
    md += ["", "T3 enthält die Ausgaben des Vormonats aus dem Regellauf. Das ist **synthetische Modellgeschichte, keine "
           "empirischen Haushaltsdaten**; im Zustand an Jev ist dies ebenfalls vermerkt (`history_note`)."]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
