"""Observation run for Jev: the v0.1 rules control the economy; Jev answers
the household budget decision for a small sample and is only logged.

Outputs (in the experiment's output directory):
  jev_log.jsonl    one line per request: request, raw response, served model,
                   tokens, cost, latency, errors, rule decision, comparison
  summary.json     totals, error counts, cost, agreement with the rule
  report.md        readable table of all observed decisions
No credentials are written anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..behavior.jev.client import JevClient, MissingKeyError, ReplayClient
from ..behavior.jev.household_budget import (DECISION_VERSION, PROBABILITY_SEMANTICS, JevBudgetObserver,
                                             build_request, write_summary)
from ..config import config_hash, deep_merge, load_yaml
from ..model import Economy
from .runner import _git, records_hash


def load_spec(path: str | Path) -> tuple[dict, dict]:
    path = Path(path)
    spec = load_yaml(path)
    base = load_yaml((path.parent / spec["base"]).resolve())
    cfg = deep_merge(base, spec.get("scenario") or {})
    return spec, cfg


def make_client(jev: dict, mode: str, replay_log: str | Path | None):
    if mode == "live":
        return JevClient(endpoint=jev["endpoint"], timeout=float(jev["timeout_s"]), retries=int(jev["retries"]))
    if mode == "replay":
        if not replay_log or not Path(replay_log).exists():
            raise FileNotFoundError(f"replay log {replay_log!r} not found")
        return ReplayClient(replay_log)
    raise ValueError(f"unknown Jev mode {mode!r} (live | replay)")


def run_observation(spec_path: str | Path, out_dir: str | Path | None = None, mode: str | None = None,
                    replay_log: str | Path | None = None, client=None, log=print) -> dict:
    spec, cfg = load_spec(spec_path)
    jev = spec["jev"]
    mode = mode or jev["mode"]
    out = Path(out_dir or spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    replay_log = replay_log or jev.get("replay_log")
    if mode == "replay" and replay_log and Path(replay_log).resolve() == (out / "jev_log.jsonl").resolve():
        raise ValueError("replay output directory must differ from the directory of the replay log")
    client = client or make_client(jev, mode, replay_log)

    seed = int(spec["seed"])
    observer = JevBudgetObserver(client, jev, out / "jev_log.jsonl", log=log)
    eco = Economy(cfg, seed, models={"household_observer": observer})
    eco.run()
    observed_hash = records_hash(eco.records)
    reference_hash = records_hash(Economy(cfg, seed).run())

    meta = {
        "decision": DECISION_VERSION,
        "probability_semantics": PROBABILITY_SEMANTICS,
        "mode": mode,
        "model_requested": jev["model"],
        "endpoint": jev["endpoint"],
        "seed": seed,
        "config_sha256_16": config_hash(cfg),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "economy_unchanged_by_observation": observed_hash == reference_hash,
        "replay_log": str(replay_log) if mode == "replay" else None,
    }
    summary = write_summary(observer.rows, out / "summary.json", meta)
    write_report(observer.rows, summary, out / "report.md")
    if not summary["economy_unchanged_by_observation"]:
        raise RuntimeError("observation changed the simulated economy")
    return summary


def ping(spec_path: str | Path, out_path: str | Path, client=None) -> dict:
    """One real request with a fixed example household, to check access,
    response format, served model, latency and cost."""
    spec, _ = load_spec(spec_path)
    jev = spec["jev"]
    client = client or make_client(jev, "live", None)
    body, options = build_request(
        jev["model"], employed=True, net_income=240_000, savings=800_000, deposits=1_020_000,
        price_now=16.2, price_usual=9.0, energy_cost=19_000, fractions=[float(f) for f in jev["budget_fractions"]])
    rec = client.decide(body)
    from ..behavior.jev.household_budget import parse_choice  # local import keeps module graph flat

    result = {"type": "ping", "options_cents": options, **rec.to_dict()}
    if rec.status == "ok":
        try:
            choice, probs, conf = parse_choice(rec.response, list(options))
            result.update(parsed={"choice": choice, "scores": probs, "confidence": conf})
        except Exception as e:  # noqa: BLE001 - report the exact problem
            result.update(status="error", error_kind=getattr(e, "kind", "error"), error=str(e))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def write_report(rows: list[dict], s: dict, path: Path) -> None:
    md = [f"# Jev-Beobachtung: {s['decision']}", "",
          "Modus **Beobachtung**: Die v0.1-Regel steuert die Wirtschaft; Jev beantwortet dieselbe "
          "Budgetentscheidung für eine Stichprobe und wird nur protokolliert. Jevs Wahrscheinlichkeiten "
          "sind modellinterne Scores, keine empirischen Entscheidungswahrscheinlichkeiten.", "",
          f"- Modus: {s['mode']}" + (" (Antworten aus Log, kein Netz)" if s["replayed"] else ""),
          f"- Angefragtes Modell: `{s['model_requested']}`; geantwortet: "
          + (", ".join(f"`{m}`" for m in s["models_served"]) or "–"),
          f"- Anfragen: {s['requests']}, erfolgreich: {s['ok']}, Fehler: {s['errors']} {s['errors_by_kind'] or ''}",
          f"- Kosten gesamt: {s['cost_usd_total']} USD; je Entscheidung: {s['cost_usd_per_decision']} USD",
          f"- Latenz Median / Maximum: {s['latency_s_median']} s / {s['latency_s_max']} s",
          f"- Wirtschaft durch Beobachtung unverändert (bitgleich zum reinen Regellauf): "
          f"{'ja' if s['economy_unchanged_by_observation'] else 'NEIN'}",
          f"- Gleiche Option wie die Regel (nächstliegende Option zum Regelbudget): {s['same_option_as_rule_share']}",
          f"- Abstand in Optionsstufen (Jev − Regel): {s['option_steps_vs_rule']}",
          f"- Medianer relativer Budgetunterschied Jev gegenüber Regel: {s['budget_diff_vs_rule_rel_median']}",
          f"- Code: `{s['git_commit'][:12]}`" + (" (mit uncommitteten Änderungen)" if s["git_dirty"] else ""), "",
          "## Je Monat", "", "| Monat | n | gleiche Option | mittlere Stufen Jev − Regel |", "|---|---|---|---|"]
    md += [f"| {t} | {m['n']} | {m['same_option_as_rule']} | {m['mean_option_steps']:.2f} |" for t, m in s["by_month"].items()]
    md += ["", "## Einzelentscheidungen", "",
           "Beträge in €. Optionen b1…b5 = 60/75/90/100/110 % des Einkommens nach Energierechnung (gerundet, "
           "höchstens verfügbares Geld).", "",
           "| Monat | HH | erwerbstätig | Netto | Ersparnis | Energie jetzt/gewohnt ct | Energierechnung | Optionen | Regel | Jev | Scores | Status |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        h = r["request"]["state"]["household"]
        opts = "/".join(str(v // 100) for v in r["options_cents"].values())
        scores = " ".join(f"{k}:{v:.2f}" for k, v in (r.get("jev_scores") or {}).items())
        jev = f"{r['jev_choice']} ({r['jev_budget_cents'] // 100})" if r.get("jev_choice") else "–"
        status = r["status"] if r["status"] == "ok" else f"{r['error_kind']}: {r['error']}"
        md.append(f"| {r['t']} | {r['household']} | {'ja' if h['employment'] == 'employed' else 'nein'} | "
                  f"{h['net_income_this_month_eur']} | {h['savings_before_this_months_income_eur']} | "
                  f"{h['energy_price_now_ct_per_kwh']}/{h['energy_price_usually_paid_ct_per_kwh']} | "
                  f"{h['energy_bill_this_month_eur']} | {opts} | {round(r['rule_budget_cents'] / 100)} "
                  f"({r['rule_nearest_option']}) | {jev} | {scores} | {status} |")
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


__all__ = ["run_observation", "ping", "MissingKeyError"]
