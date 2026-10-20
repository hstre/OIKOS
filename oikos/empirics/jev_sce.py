"""Registered prediction test: Jev versus simple references on SCE QSP13new.

Pipeline (configs/experiments/sce_validation.yaml):
  1. requests for the adjustment sample (400), the sealed test sample (800) and
     the technical control (40 adjustment respondents x 5 extra requests);
  2. models M0 prior, M1 multinomial logit, M2 Jev raw, M3 Jev calibrated,
     M4 stacked (M1 + Jev), fitted only on training / adjustment data;
  3. metrics on the test sample and the registered decision rule.

Jev is asked which answer the respondent is most likely to give to the survey
question; the target is a stated answer to a hypothetical scenario, not
observed behaviour. Scores are model-internal until calibrated; even
calibrated, they are predicted probabilities of a survey answer.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..behavior.jev.client import JevClient, ReplayClient, request_hash
from ..behavior.jev.household_budget import parse_choice
from ..experiments.jev_robustness import CostGuard
from ..experiments.runner import _git
from .mlogit import MultinomialLogit, auc, brier, log_loss
from .sce import COLLAPSE_3, OUTCOME_LABELS_3, OUTCOME_LABELS_7

QUESTION_ID = "response_to_income_loss"
SURVEY_QUESTION = ("Now imagine that next year you were to find yourself with 10% less household income. "
                   "What would you do?")
INSTRUCTIONS = (f'The respondent is asked: "{SURVEY_QUESTION}" Which of the listed answers is this respondent '
                "most likely to give? Use only the information in the state.")
CONTEXT = ("A respondent to a monthly household survey in the United States (Survey of Consumer Expectations). "
           "The information below was given by the respondent in the same month.")
CATEGORICAL = ["age_group", "education", "household_income_group", "employment"]
NUMERIC = ["job_loss_chance_12m", "expected_income_change_12m", "expected_spending_change_12m",
           "debt_payment_miss_chance_3m"]


# ------------------------------------------------------------- requests
def respondent_state(row: pd.Series) -> dict:
    def num(v, unit=""):
        return None if pd.isna(v) else (int(v) if float(v).is_integer() else round(float(v), 1))

    r = {
        "age_group": row.age_group if pd.notna(row.age_group) else "unknown",
        "education": row.education if pd.notna(row.education) else "unknown",
        "household_income_last_12_months_usd": row.household_income_group if pd.notna(row.household_income_group) else "unknown",
        "employment": row.employment,
        "percent_chance_of_losing_job_next_12_months": (num(row.job_loss_chance_12m) if pd.notna(row.job_loss_chance_12m)
                                                       else "not asked (not working)"),
        "expected_change_of_household_income_next_12_months_percent": num(row.expected_income_change_12m),
        "expected_change_of_household_spending_next_12_months_percent": num(row.expected_spending_change_12m),
        "percent_chance_of_missing_a_debt_payment_next_3_months": num(row.debt_payment_miss_chance_3m),
    }
    return r


def build_request(row: pd.Series, spec: dict, presentation: int, placebo: bool = False) -> tuple[dict, dict[str, int]]:
    order = spec["presentations"]["orders"][presentation]
    ids = spec["presentations"]["identifiers"]
    code = {a: ids[(a - 1 + 3 * presentation) % len(ids)] for a in OUTCOME_LABELS_7}
    respondent = respondent_state(row)
    if placebo:
        respondent.update(spec["technical_control"]["placebo_field"])
    body = {"model": spec["jev"]["model"],
            "state": {"context": CONTEXT, "respondent": respondent},
            "questions": {QUESTION_ID: {"type": "choice", "instructions": INSTRUCTIONS,
                                        "criteria": {code[a]: OUTCOME_LABELS_7[a] for a in order}}}}
    return body, {code[a]: a for a in OUTCOME_LABELS_7}


def jobs(df: pd.DataFrame, spec: dict) -> list[dict]:
    out = []
    for _, row in df[df.set.isin(["adjustment", "test"])].sort_values("hash").iterrows():
        out.append({"userid": int(row.userid), "set": row.set, "kind": "main", "presentation": int(row.presentation),
                    "placebo": False})
    n_pres = len(spec["presentations"]["orders"])
    for _, row in df[df.technical_control].sort_values("hash").iterrows():
        p0 = int(row.presentation)
        for p in range(n_pres):
            if p != p0:
                out.append({"userid": int(row.userid), "set": "control", "kind": "other_presentation",
                            "presentation": p, "placebo": False})
        out.append({"userid": int(row.userid), "set": "control", "kind": "repeat", "presentation": p0, "placebo": False})
        out.append({"userid": int(row.userid), "set": "control", "kind": "placebo", "presentation": p0, "placebo": True})
    return out


def run(spec: dict, df: pd.DataFrame, out_dir, mode: str = "live", replay_log=None, client=None, log=print) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    todo = jobs(df, spec)
    if len(todo) > spec["limits"]["max_requests"]:
        raise ValueError(f"{len(todo)} requests exceed the registered limit")
    if client is None:
        j = spec["jev"]
        client = (JevClient(endpoint=j["endpoint"], timeout=float(j["timeout_s"]), retries=int(j["retries"]))
                  if mode == "live" else ReplayClient(replay_log))
    guard = CostGuard(float(spec["limits"]["cost_usd"]))
    by_id = df.set_index("userid")
    rows = []
    with open(out / "jev_log.jsonl", "w", encoding="utf-8") as f:
        for job in todo:
            body, answer_of = build_request(by_id.loc[job["userid"]], spec, job["presentation"], job["placebo"])
            row = {"type": "call", **job, "answer_of_id": answer_of,
                   "shown_order": list(body["questions"][QUESTION_ID]["criteria"])}
            if mode == "live" and not guard.allow():
                row.update(status="skipped_cost_limit", request=body, request_sha256=request_hash(body))
            else:
                rec = client.decide(body)
                guard.add(0.0 if rec.replayed else rec.cost_usd)
                row.update(rec.to_dict())
                if rec.status == "ok":
                    try:
                        choice, scores, conf = parse_choice(rec.response, list(answer_of), QUESTION_ID)
                        row.update(jev_answer=answer_of[choice], jev_scores_by_answer={
                            str(answer_of[k]): v for k, v in scores.items()}, jev_confidence=conf)
                    except Exception as e:  # noqa: BLE001 - recorded, never replaced
                        row.update(status="error", error_kind=getattr(e, "kind", "error"), error=str(e)[:300])
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    log(f"{sum(r['status'] == 'ok' for r in rows)}/{len(rows)} requests ok")
    result = analyse(spec, df, rows)
    result.update(mode=mode, git_commit=_git("rev-parse", "HEAD"),
                  git_dirty=bool(_git("status", "--porcelain", "--untracked-files=no")))
    (out / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(result, out / "report.md")
    return result


# ------------------------------------------------------------- models
def design(df: pd.DataFrame, levels: dict | None = None) -> tuple[np.ndarray, dict]:
    if levels is None:
        levels = {c: sorted(df[c].fillna("unknown").unique()) for c in CATEGORICAL}
    cols = []
    for c in CATEGORICAL:
        v = df[c].fillna("unknown")
        cols += [(v == lv).astype(float).to_numpy() for lv in levels[c][1:]]
    for c in NUMERIC:
        x = df[c].to_numpy(dtype=float)
        miss = np.isnan(x)
        cols += [np.where(miss, 0.0, np.clip(x, -100, 100) / 100.0), miss.astype(float)]
    return np.column_stack(cols), levels


def jev_probs(rows: list[dict], userids: np.ndarray, floor: float = 1e-4) -> tuple[np.ndarray, np.ndarray]:
    """Main-request Jev scores per respondent as 7- and 3-class arrays (NaN rows if missing)."""
    main = {r["userid"]: r for r in rows if r["kind"] == "main" and r["status"] == "ok"}
    p7 = np.full((len(userids), 7), np.nan)
    for i, u in enumerate(userids):
        r = main.get(int(u))
        if r:
            p7[i] = [r["jev_scores_by_answer"][str(a)] for a in range(1, 8)]
    p3 = np.full((len(userids), 3), np.nan)
    for a, c in COLLAPSE_3.items():
        p3[:, c] = np.nan_to_num(p3[:, c]) + p7[:, a - 1]
    p3[np.isnan(p7).any(axis=1)] = np.nan

    def norm(p):
        p = np.maximum(p, floor)
        return p / p.sum(axis=1, keepdims=True)

    return norm(p7), norm(p3)


def _bootstrap(diff: np.ndarray, n: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), (n, len(diff)))
    m = diff[idx].mean(axis=1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def _tvd(a: dict, b: dict) -> float:
    return 0.5 * sum(abs(a[k] - b[k]) for k in a)


def analyse(spec: dict, df: pd.DataFrame, rows: list[dict]) -> dict:
    train = df[df.period == "train"].reset_index(drop=True)
    adj = df[df.set == "adjustment"].reset_index(drop=True)
    test = df[df.set == "test"].reset_index(drop=True)
    X_tr, levels = design(train)
    y_tr = train.y3.to_numpy()

    # M0, M1
    prior = np.bincount(y_tr, minlength=3) / len(y_tr)
    m1 = MultinomialLogit(l2=1.0).fit(X_tr, y_tr, 3)
    P = {"M0_prior": np.tile(prior, (len(test), 1)), "M1_logit": m1.predict_proba(design(test, levels)[0])}

    # Jev scores
    _, j_adj = jev_probs(rows, adj.userid.to_numpy())
    _, j_test = jev_probs(rows, test.userid.to_numpy())
    p7_test, _ = jev_probs(rows, test.userid.to_numpy())
    ok_adj = ~np.isnan(j_adj).any(axis=1)
    ok_test = ~np.isnan(j_test).any(axis=1)
    out = {"n_train": len(train), "n_adjustment": int(len(adj)), "n_test": int(len(test)),
           "n_adjustment_with_jev": int(ok_adj.sum()), "n_test_with_jev": int(ok_test.sum())}
    keep = ok_test
    y = test.y3.to_numpy()[keep]
    P = {k: v[keep] for k, v in P.items()}
    P["M2_jev_raw"] = j_test[keep]

    # M3: calibration of Jev on the adjustment sample
    y_adj = adj.y3.to_numpy()[ok_adj]
    m3 = MultinomialLogit(l2=1.0).fit(np.log(j_adj[ok_adj]), y_adj, 3)
    P["M3_jev_calibrated"] = m3.predict_proba(np.log(j_test[keep]))

    # M4: stacked; M1 for adjustment respondents is cross-fitted (5 folds within training)
    folds = (train.hash % 5).to_numpy()
    m1_cf = np.zeros((len(train), 3))
    for k in range(5):
        fit = MultinomialLogit(l2=1.0).fit(X_tr[folds != k], y_tr[folds != k], 3)
        m1_cf[folds == k] = fit.predict_proba(X_tr[folds == k])
    pos = {u: i for i, u in enumerate(train.userid)}
    m1_adj = m1_cf[[pos[u] for u in adj.userid[ok_adj]]]
    Z_adj = np.hstack([np.log(m1_adj), np.log(j_adj[ok_adj])])
    m4 = MultinomialLogit(l2=1.0).fit(Z_adj, y_adj, 3)
    P["M4_stacked"] = m4.predict_proba(np.hstack([np.log(P["M1_logit"]), np.log(P["M2_jev_raw"])]))

    metrics = {}
    for name, p in P.items():
        metrics[name] = {"log_loss": log_loss(p, y), "brier": brier(p, y), "accuracy": float(np.mean(p.argmax(1) == y)),
                         "auc_any_cut": auc(p[:, 0] + p[:, 1], y != 2), "auc_full_cut": auc(p[:, 0], y == 0),
                         "mean_predicted_shares": p.mean(axis=0).round(4).tolist()}
    out["observed_test_shares_y3"] = (np.bincount(y, minlength=3) / len(y)).round(4).tolist()
    out["metrics_y3"] = metrics

    # secondary: 7 classes (M0, M1, Jev raw)
    y7 = test.y7.to_numpy()[keep] - 1
    prior7 = np.bincount(train.y7.to_numpy() - 1, minlength=7) / len(train)
    m1_7 = MultinomialLogit(l2=1.0).fit(X_tr, train.y7.to_numpy() - 1, 7)
    out["metrics_y7_log_loss"] = {"M0_prior": log_loss(np.tile(prior7, (len(y7), 1)), y7),
                                  "M1_logit": log_loss(m1_7.predict_proba(design(test, levels)[0])[keep], y7),
                                  "M2_jev_raw": log_loss(p7_test[keep], y7)}

    # primary decision
    eps = 1e-6
    ll = lambda p: -np.log(np.clip(p[np.arange(len(y)), y], eps, 1))  # noqa: E731
    diff = ll(P["M4_stacked"]) - ll(P["M1_logit"])
    lo, hi = _bootstrap(diff, 2000, 20261020)
    out["primary"] = {"delta_log_loss_M4_minus_M1": float(diff.mean()), "ci95": [lo, hi],
                      "jev_adds_predictive_value": bool(hi < 0)}
    d3 = ll(P["M3_jev_calibrated"]) - ll(P["M1_logit"])
    out["secondary_delta_M3_minus_M1"] = {"mean": float(d3.mean()), "ci95": list(_bootstrap(d3, 2000, 20261021))}

    # technical control
    ok = {(r["userid"], r["kind"], r["presentation"]): r["jev_scores_by_answer"] for r in rows if r["status"] == "ok"}
    main = {r["userid"]: r for r in rows if r["kind"] == "main" and r["status"] == "ok"}
    tv = {"other_presentation": [], "repeat": [], "placebo": []}
    for (u, kind, p), s in ok.items():
        if kind in tv and u in main:
            tv[kind].append(_tvd(s, main[u]["jev_scores_by_answer"]))
    out["technical_control"] = {k: {"n": len(v), "median_tvd": float(np.median(v)) if v else None,
                                    "max_tvd": float(np.max(v)) if v else None} for k, v in tv.items()}
    pres = out["technical_control"]["other_presentation"]["median_tvd"]
    out["technical_control"]["presentation_sensitive"] = bool(pres is not None and pres > 0.2)

    costs = [r["cost_usd"] for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    errors = {}
    for r in rows:
        if r["status"] != "ok":
            k = r.get("error_kind") or r["status"]
            errors[k] = errors.get(k, 0) + 1
    out.update(requests=len(rows), errors_by_kind=errors, cost_usd_logged=round(sum(costs), 8),
               models_served=sorted({r["model_served"] for r in rows if r.get("model_served")}),
               coefficients={"M4_stacked": m4.coef_.round(4).tolist(), "M3_jev_calibrated": m3.coef_.round(4).tolist()})
    return out


def write_report(s: dict, path: Path) -> None:
    md = ["# SCE-Vorhersagetest: Jev gegen einfache Referenzen", "",
          "Ziel: angegebene Antwort auf QSP13new (hypothetischer Einkommensrückgang um 10 %). Selbstauskunft zu einem "
          "hypothetischen Szenario, kein beobachtetes Verhalten. Source: Survey of Consumer Expectations, © 2013-2026 "
          "Federal Reserve Bank of New York; modified for this analysis.", "",
          f"- Stichproben: Training {s['n_train']}, Anpassung {s['n_adjustment']} ({s['n_adjustment_with_jev']} mit Jev), "
          f"Test {s['n_test']} ({s['n_test_with_jev']} mit Jev)",
          f"- Anfragen {s['requests']}, Fehler {s['errors_by_kind'] or 0}, Kosten {s['cost_usd_logged']} USD, "
          f"Modelle {', '.join(s['models_served']) or '–'}",
          f"- Code `{s['git_commit'][:12]}`", "",
          "## Primäres Kriterium (vorab festgelegt)", "",
          f"Δ Log-Loss M4 (Logit + Jev) − M1 (Logit): {s['primary']['delta_log_loss_M4_minus_M1']:+.4f}, "
          f"95 %-Intervall [{s['primary']['ci95'][0]:+.4f}, {s['primary']['ci95'][1]:+.4f}] → "
          f"**{'zusätzlicher Vorhersagenutzen' if s['primary']['jev_adds_predictive_value'] else 'kein nachgewiesener zusätzlicher Vorhersagenutzen'}**", "",
          "## Kennzahlen (Test, drei Klassen: volle Kürzung / teilweise / keine)", "",
          f"Beobachtete Anteile: {s['observed_test_shares_y3']}", "",
          "| Modell | Log-Loss | Brier | Trefferquote | AUC Kürzung ja/nein | AUC volle Kürzung | mittlere vorhergesagte Anteile |",
          "|---|---|---|---|---|---|---|"]
    for k, m in s["metrics_y3"].items():
        md.append(f"| {k} | {m['log_loss']:.4f} | {m['brier']:.4f} | {m['accuracy']:.3f} | {m['auc_any_cut']:.3f} | "
                  f"{m['auc_full_cut']:.3f} | {m['mean_predicted_shares']} |")
    md += ["", f"Sieben Klassen, Log-Loss: {s['metrics_y7_log_loss']}", "",
           f"M3 − M1: {s['secondary_delta_M3_minus_M1']}", "",
           "## Technische Kontrolle (Darstellung)", "", f"{s['technical_control']}", ""]
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
