"""Controlled paired test of the Jev budget question (observation only).

Pairs of constructed household cases differ in exactly one feature. Both
cases of a pair see the same fixed euro options under the same presentation
(order and neutral identifiers). Five presentations form a Latin square, so
every amount appears once at every position and identifiers rotate
independently. Design, hypotheses and decision rule are pre-registered in
configs/experiments/jev_pairs.yaml and docs/07_jev_paartest.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..behavior.jev.client import JevClient, ReplayClient, request_hash
from ..behavior.jev.household_budget import INSTRUCTIONS, PROBABILITY_SEMANTICS, QUESTION_ID, parse_choice
from ..config import load_yaml
from .jev_robustness import CostGuard
from .runner import _git, cpu_features

FIELD_ORDER = ["employment", "net_income_this_month_eur", "savings_before_this_months_income_eur",
               "energy_price_now_ct_per_kwh", "energy_price_usually_paid_ct_per_kwh",
               "energy_bill_this_month_eur", "money_available_after_energy_bill_eur"]


# --------------------------------------------------------------- design
def household(spec: dict, override: dict) -> dict:
    h = {**spec["base"], **override}
    h["money_available_after_energy_bill_eur"] = (h["savings_before_this_months_income_eur"]
                                                 + h["net_income_this_month_eur"] - h["energy_bill_this_month_eur"])
    ordered = {k: h[k] for k in FIELD_ORDER}
    ordered.update({k: v for k, v in h.items() if k not in ordered})  # pair-specific extra fields last
    return ordered


def presentation(spec: dict, j: int) -> tuple[list[int], dict[int, str]]:
    """Order of amount indices and identifier per amount index for presentation j."""
    n = len(spec["options_eur"])
    ids = spec["presentations"]["identifiers"]
    order = [(k + j) % n for k in range(n)]
    code = {a: ids[(a + 2 * j) % n] for a in range(n)}
    return order, code


def build_body(spec: dict, hh: dict, j: int) -> tuple[dict, dict[str, int]]:
    order, code = presentation(spec, j)
    amounts = spec["options_eur"]
    criteria = {code[a]: f"Spend about {amounts[a]} €." for a in order}
    body = {"model": spec["jev"]["model"],
            "state": {"context": " ".join(spec["context"].split()), "household": hh},
            "questions": {QUESTION_ID: {"type": "choice", "instructions": INSTRUCTIONS, "criteria": criteria}}}
    return body, {code[a]: amounts[a] for a in range(len(amounts))}


def jobs(spec: dict) -> list[dict]:
    out = []
    for pair, p in spec["pairs"].items():
        for case in ("A", "B"):
            hh = household(spec, p[case])
            for j in range(spec["presentations"]["count"]):
                out.append({"pair": pair, "case": case, "presentation": j, "repeat": False, "household": hh})
            out.append({"pair": pair, "case": case, "presentation": spec["presentations"]["repeat_presentation"],
                        "repeat": True, "household": hh})
    # fixed, shuffled execution order so that time trends do not line up with cases
    rng = np.random.default_rng(20261019)
    return [out[i] for i in rng.permutation(len(out))]


# ------------------------------------------------------------------ run
def run_pairs(spec_path, out_dir=None, mode: str = "live", replay_log=None, client=None, log=print) -> dict:
    spec = load_yaml(spec_path)
    out = Path(out_dir or spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    todo = jobs(spec)
    if len(todo) > int(spec["limits"]["max_requests"]):
        raise ValueError(f"{len(todo)} requests exceed the limit {spec['limits']['max_requests']}")
    if client is None:
        if mode == "live":
            j = spec["jev"]
            client = JevClient(endpoint=j["endpoint"], timeout=float(j["timeout_s"]), retries=int(j["retries"]))
        else:
            client = ReplayClient(replay_log)
    guard = CostGuard(float(spec["limits"]["cost_usd"]))
    rows = []
    log_path = out / "jev_log.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for job in todo:
            body, amount_of = build_body(spec, job["household"], job["presentation"])
            shown = list(body["questions"][QUESTION_ID]["criteria"])
            row = {"type": "call", "test": spec["name"], "pair": job["pair"], "case": job["case"],
                   "presentation": job["presentation"], "repeat": job["repeat"], "constructed_case": True,
                   "probability_semantics": PROBABILITY_SEMANTICS, "shown_order": shown, "amount_of": amount_of}
            if mode == "live" and not guard.allow():
                row.update(status="skipped_cost_limit", request=body, request_sha256=request_hash(body))
            else:
                rec = client.decide(body)
                guard.add(0.0 if rec.replayed else rec.cost_usd)
                row.update(rec.to_dict())
                if rec.status == "ok":
                    try:
                        choice, scores, conf = parse_choice(rec.response, list(amount_of))
                        hh = job["household"]
                        w = sum(scores[k] * amount_of[k] for k in scores)
                        row.update(jev_choice=choice, chosen_eur=amount_of[choice],
                                   chosen_position=shown.index(choice) + 1, scores=scores,
                                   scores_by_eur={str(amount_of[k]): scores[k] for k in scores},
                                   confidence=conf, weighted_eur=w,
                                   quota_net_income=w / hh["net_income_this_month_eur"],
                                   quota_after_energy=w / (hh["net_income_this_month_eur"] - hh["energy_bill_this_month_eur"]))
                    except Exception as e:  # noqa: BLE001 - recorded, never replaced
                        row.update(status="error", error_kind=getattr(e, "kind", "error"), error=str(e)[:300])
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    summary = analyse(spec, rows, mode, guard)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(spec, summary, out / "report.md")
    log(f"{summary['requests_ok']}/{len(rows)} ok, cost {summary['cost_usd_total']} USD")
    return summary


# ------------------------------------------------------------- analysis
def _tvd_eur(a: dict, b: dict) -> float:
    return 0.5 * sum(abs(a[k] - b[k]) for k in a)


def analyse(spec: dict, rows: list[dict], mode: str, guard: CostGuard) -> dict:
    ok = [r for r in rows if r["status"] == "ok"]
    first = {(r["pair"], r["case"], r["presentation"]): r for r in ok if not r["repeat"]}
    rep = {(r["pair"], r["case"]): r for r in ok if r["repeat"]}
    j0 = spec["presentations"]["repeat_presentation"]
    noise_eur, noise_tvd = [], []
    for (pair, case), r in rep.items():
        f0 = first.get((pair, case, j0))
        if f0:
            noise_eur.append(abs(r["weighted_eur"] - f0["weighted_eur"]))
            noise_tvd.append(_tvd_eur(r["scores_by_eur"], f0["scores_by_eur"]))
    noise = float(np.median(noise_eur)) if noise_eur else None
    crit = spec["criteria"]
    n_pres = spec["presentations"]["count"]
    pairs = {}
    for pair in spec["pairs"]:
        per = []
        for j in range(n_pres):
            a, b = first.get((pair, "A", j)), first.get((pair, "B", j))
            if not (a and b):
                continue
            per.append({"presentation": j,
                        "A_weighted_eur": a["weighted_eur"], "B_weighted_eur": b["weighted_eur"],
                        "delta_weighted_eur": b["weighted_eur"] - a["weighted_eur"],
                        "A_chosen_eur": a["chosen_eur"], "B_chosen_eur": b["chosen_eur"],
                        "A_chosen_position": a["chosen_position"], "B_chosen_position": b["chosen_position"],
                        "A_choice_id": a["jev_choice"], "B_choice_id": b["jev_choice"],
                        "tvd_A_B": _tvd_eur(a["scores_by_eur"], b["scores_by_eur"]),
                        "A_quota_net": a["quota_net_income"], "B_quota_net": b["quota_net_income"],
                        "A_quota_after_energy": a["quota_after_energy"], "B_quota_after_energy": b["quota_after_energy"]})
        deltas = [p["delta_weighted_eur"] for p in per]
        signs = np.sign(deltas) if deltas else np.array([])
        same_sign = int(max((signs > 0).sum(), (signs < 0).sum())) if deltas else 0
        med = float(np.median(deltas)) if deltas else None
        complete = len(per) == n_pres
        distinguished = bool(complete and noise is not None and same_sign >= crit["sign_agreement_required"]
                             and abs(med) > crit["noise_multiple"] * noise)
        mean_scores = {}
        for case in ("A", "B"):
            vals = [first[(pair, case, j)]["scores_by_eur"] for j in range(n_pres) if (pair, case, j) in first]
            if vals:
                mean_scores[case] = {k: float(np.mean([v[k] for v in vals])) for k in vals[0]}
        pairs[pair] = {"feature": spec["pairs"][pair]["feature"], "presentations_complete": complete,
                       "per_presentation": per, "median_delta_weighted_eur": med,
                       "min_delta": float(min(deltas)) if deltas else None,
                       "max_delta": float(max(deltas)) if deltas else None,
                       "same_sign_presentations": same_sign, "direction": (None if med is None else
                                                                           "higher" if med > 0 else "lower" if med < 0 else "none"),
                       "consistently_distinguished": distinguished,
                       "median_tvd_A_B": float(np.median([p["tvd_A_B"] for p in per])) if per else None,
                       "mean_scores_by_eur_over_presentations": mean_scores}
    costs = [r["cost_usd"] for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    errors = {}
    for r in rows:
        if r["status"] != "ok":
            k = r.get("error_kind") or r["status"]
            errors[k] = errors.get(k, 0) + 1
    pos_counts, id_counts = {}, {}
    for r in ok:
        pos_counts[str(r["chosen_position"])] = pos_counts.get(str(r["chosen_position"]), 0) + 1
        id_counts[r["jev_choice"]] = id_counts.get(r["jev_choice"], 0) + 1
    return {"name": spec["name"], "mode": mode, "probability_semantics": PROBABILITY_SEMANTICS,
            "git_commit": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
            "numpy_x86_v4": cpu_features().get("X86_V4", False),
            "requests": len(rows), "requests_ok": len(ok), "errors_by_kind": errors,
            "models_served": sorted({r["model_served"] for r in rows if r.get("model_served")}),
            "cost_usd_total": round(sum(costs), 8) if costs and mode == "live" else 0.0,
            "cost_usd_logged": round(sum(costs), 8) if costs else 0.0,
            "noise_eur_median": noise, "noise_eur_all": noise_eur,
            "noise_tvd_median": float(np.median(noise_tvd)) if noise_tvd else None,
            "chosen_position_counts": dict(sorted(pos_counts.items())),
            "chosen_id_counts": dict(sorted(id_counts.items())),
            "pairs": pairs}


def write_report(spec: dict, s: dict, path: Path) -> None:
    hyp = {"P0_placebo": "none", "P1_job_security": "lower", "P2_savings": "higher",
           "P3_last_month_spending": "higher", "P4_energy_price": "lower", "P5_income": "higher"}
    de = {"higher": "höher", "lower": "niedriger", "none": "kein Unterschied", None: "–"}
    md = [f"# Jev-Paartest: {s['name']}", "",
          "Konstruierte Fälle, nur Beobachtung. Scores sind modellinterne Werte, keine Entscheidungswahrscheinlichkeiten. "
          "Vorab festgelegte Regel: konsistent unterschieden = gleiches Vorzeichen in allen 5 Darstellungen und "
          "|Median Δ| > 2 × Rauschen.", "",
          f"- Modus {s['mode']}; Anfragen {s['requests']}, erfolgreich {s['requests_ok']}, Fehler {s['errors_by_kind'] or 0}",
          f"- Modelle: {', '.join(s['models_served']) or '–'}; Kosten {s['cost_usd_logged']} USD",
          f"- Rauschen (Median |Δ gewichtetes Budget| bei Wiederholung): {s['noise_eur_median']:.1f} € "
          f"(TVD-Median {s['noise_tvd_median']:.3f})" if s["noise_eur_median"] is not None else "- Rauschen: –",
          f"- Gewählte Positionen über alle Anfragen: {s['chosen_position_counts']}; Kennungen: {s['chosen_id_counts']}",
          f"- Code `{s['git_commit'][:12]}`", "",
          "## Ergebnis je Paar", "",
          "| Paar | Merkmal | Hypothese | Median Δ gewichtetes Budget (min…max) | gleiches Vorzeichen | konsistent unterschieden | Richtung | TVD A–B Median |",
          "|---|---|---|---|---|---|---|---|"]
    for pair, p in s["pairs"].items():
        md.append(f"| {pair} | {p['feature']} | {de[hyp[pair]]} | "
                  + (f"{p['median_delta_weighted_eur']:+.0f} € ({p['min_delta']:+.0f}…{p['max_delta']:+.0f})" if p["median_delta_weighted_eur"] is not None else "–")
                  + f" | {p['same_sign_presentations']}/5 | {'ja' if p['consistently_distinguished'] else 'nein'} | "
                  f"{de[p['direction']]} | {p['median_tvd_A_B']:.3f} |" if p["median_tvd_A_B"] is not None else " – |")
    md += ["", "## Je Darstellung: Eurobeträge, Quoten, gewählte Optionen", ""]
    for pair, p in s["pairs"].items():
        md += [f"### {pair}: {p['feature']}", "",
               "| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |",
               "|---|---|---|---|---|---|---|---|---|"]
        for r in p["per_presentation"]:
            md.append(f"| {r['presentation']} | {r['A_weighted_eur']:.0f} | {r['B_weighted_eur']:.0f} | {r['delta_weighted_eur']:+.0f} | "
                      f"{r['A_chosen_eur']} ({r['A_chosen_position']}, {r['A_choice_id']}) | {r['B_chosen_eur']} ({r['B_chosen_position']}, {r['B_choice_id']}) | "
                      f"{r['A_quota_net']:.0%} / {r['A_quota_after_energy']:.0%} | {r['B_quota_net']:.0%} / {r['B_quota_after_energy']:.0%} | {r['tvd_A_B']:.3f} |")
        ms = p["mean_scores_by_eur_over_presentations"]
        if ms:
            keys = list(ms["A"])
            md += ["", "Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):", "",
                   "| Fall | " + " | ".join(f"{k} €" for k in keys) + " |", "|---|" + "---|" * len(keys)]
            md += [f"| {c} | " + " | ".join(f"{ms[c][k]:.2f}" for k in keys) + " |" for c in ("A", "B") if c in ms]
        md.append("")
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
