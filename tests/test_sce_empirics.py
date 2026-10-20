"""Empirical SCE test pipeline on synthetic data (no download, no network)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from oikos.behavior.jev.client import JevClient
from oikos.empirics import jev_sce, sce
from oikos.empirics.mlogit import MultinomialLogit, auc, log_loss

ROOT = Path(__file__).resolve().parents[1]
SPEC = yaml.safe_load((ROOT / "configs" / "experiments" / "sce_validation.yaml").read_text())


def synthetic(n=3000, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    inc = rng.choice(["Under 50k", "50k to 100k", "Over 100k"], n)
    emp = rng.choice(["working full-time", "retired", "working part-time"], n)
    job = np.where(emp == "retired", np.nan, rng.integers(0, 60, n))
    # outcome depends on income group: low income cuts spending fully more often
    p_full = np.where(inc == "Under 50k", 0.65, 0.35)
    u = rng.random(n)
    y7 = np.where(u < p_full, 1, np.where(u < p_full + 0.25, 4, np.where(u < p_full + 0.32, 2, 7)))
    df = pd.DataFrame({
        "userid": np.arange(70000000, 70000000 + n), "date": rng.choice([201905, 202003, 202306, 202405], n),
        "weight": 1.0, "age_group": rng.choice(["Under 40", "40 to 60", "Over 60"], n),
        "education": rng.choice(["College", "Some College", "High School"], n), "household_income_group": inc,
        "employment": emp, "job_loss_chance_12m": job, "expected_income_change_12m": rng.normal(2, 5, n).round(),
        "expected_spending_change_12m": rng.normal(3, 5, n).round(), "debt_payment_miss_chance_3m": rng.integers(0, 30, n),
        "y7": y7})
    df["first_spending_date"] = df.date
    df["y3"] = df.y7.map(sce.COLLAPSE_3)
    return df


def spec_small():
    s = json.loads(json.dumps(SPEC))
    s["split"].update(adjustment_n=200, test_n=300)
    s["technical_control"]["n"] = 10
    s["limits"]["max_requests"] = 600
    return s


# ---------------------------------------------------------------- model code
def test_mlogit_recovers_structure():
    rng = np.random.default_rng(1)
    n = 40000
    X = rng.normal(size=(n, 2))
    beta = np.array([[0.5, -1.0], [1.5, 0.0], [0.0, 2.0]])  # rows: intercept, x1, x2; cols: class 1, 2
    Z = np.hstack([np.zeros((n, 1)), np.hstack([np.ones((n, 1)), X]) @ beta])
    P = np.exp(Z) / np.exp(Z).sum(1, keepdims=True)
    y = (rng.random(n)[:, None] > P.cumsum(1)).sum(1)
    m = MultinomialLogit(l2=0.0).fit(X, y, 3)
    # first-order condition of the maximum likelihood estimate
    A = np.hstack([np.ones((n, 1)), X])
    Y = np.eye(3)[y]
    grad = A.T @ (Y - m.predict_proba(X))[:, 1:]
    assert np.abs(grad).max() < 1e-6
    np.testing.assert_allclose(m.coef_, beta, atol=0.06)
    assert log_loss(m.predict_proba(X), y) < log_loss(np.tile(np.bincount(y) / len(y), (len(y), 1)), y)


def test_auc_edge_cases():
    assert auc(np.array([0.1, 0.2, 0.3, 0.4]), np.array([0, 0, 1, 1])) == 1.0
    assert auc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([0, 1, 0, 1])) == 0.5


# ------------------------------------------------------------- split, leakage
def test_split_is_deterministic_and_separated():
    df = synthetic()
    s = spec_small()
    a, b = sce.assign(df, s), sce.assign(df, s)
    pd.testing.assert_frame_equal(a, b)
    sce.check_no_leakage(a)
    assert (a.set == "adjustment").sum() == 200 and (a.set == "test").sum() == 300
    assert (a.loc[a.set == "adjustment", "period"] == "train").all()
    assert (a.loc[a.set == "adjustment", "date"] >= s["split"]["adjustment_from"]).all()
    assert a.loc[a.technical_control, "set"].eq("adjustment").all()


def test_request_contains_only_registered_context():
    df = sce.assign(synthetic(), spec_small())
    row = df.iloc[0]
    body, answer_of = jev_sce.build_request(row, SPEC, 0)
    text = json.dumps(body).lower()
    assert set(body["state"]["respondent"]) == {
        "age_group", "education", "household_income_last_12_months_usd", "employment",
        "percent_chance_of_losing_job_next_12_months", "expected_change_of_household_income_next_12_months_percent",
        "expected_change_of_household_spending_next_12_months_percent", "percent_chance_of_missing_a_debt_payment_next_3_months"}
    for forbidden in ("y3", "y7", "qsp", "userid", "hash", "period", "full_cut", "partial_cut", "no_cut"):
        assert forbidden not in text, forbidden
    assert sorted(answer_of.values()) == list(range(1, 8))
    assert "most likely to give" in body["questions"]["response_to_income_loss"]["instructions"]


def test_presentations_rotate_order_and_identifiers():
    row = sce.assign(synthetic(), spec_small()).iloc[0]
    seen = []
    for p in range(4):
        body, answer_of = jev_sce.build_request(row, SPEC, p)
        shown = list(body["questions"]["response_to_income_loss"]["criteria"])
        assert [answer_of[k] for k in shown] == SPEC["presentations"]["orders"][p]
        seen.append({a: k for k, a in answer_of.items()})
    for a in range(1, 8):
        assert len({m[a] for m in seen}) == 4  # each answer gets a different identifier in each presentation
    placebo, _ = jev_sce.build_request(row, SPEC, 0, placebo=True)
    base, _ = jev_sce.build_request(row, SPEC, 0)
    diff = set(placebo["state"]["respondent"]) - set(base["state"]["respondent"])
    assert diff == {"survey_panel_code"}


# ------------------------------------------------------------- full pipeline
def fake_client(informative: bool):
    def transport(url, body, headers, timeout):
        req = json.loads(body)
        q = req["questions"]["response_to_income_loss"]
        r = req["state"]["respondent"]
        ids = list(q["criteria"])
        label = {k: v for k, v in q["criteria"].items()}
        low = r["household_income_last_12_months_usd"] == "Under 50k"
        w = {}
        for k in ids:
            full = label[k].startswith("Cut spending by the whole")
            w[k] = (3.0 if (full and low and informative) else 1.0) * (1.2 if k == ids[0] else 1.0)
        tot = sum(w.values())
        probs = {k: v / tot for k, v in w.items()}
        resp = {"model": "typesafe/jev-1.14-20261014", "provider": "TypeSafe", "id": "x",
                "answers": {"response_to_income_loss": {"type": "choice", "choice": max(probs, key=probs.get),
                                                        "confidence": 0.3, "probabilities": probs}},
                "usage": {"input_tokens": 600, "output_tokens": 50, "cost": 0.000025}}
        return 200, json.dumps(resp).encode()
    return JevClient(api_key="sk-or-test", transport=transport, sleep=lambda s: None)


@pytest.mark.parametrize("informative", [True, False])
def test_pipeline_runs_and_replays(tmp_path, informative):
    s = spec_small()
    df = sce.assign(synthetic(), s)
    res = jev_sce.run(s, df, tmp_path / "live", client=fake_client(informative), log=lambda *_: None)
    assert res["n_test_with_jev"] == 300 and res["errors_by_kind"] == {}
    assert set(res["metrics_y3"]) == {"M0_prior", "M1_logit", "M2_jev_raw", "M3_jev_calibrated", "M4_stacked"}
    assert res["technical_control"]["repeat"]["n"] == 10 and res["technical_control"]["placebo"]["n"] == 10
    rep = jev_sce.run(s, df, tmp_path / "rep", mode="replay", replay_log=tmp_path / "live" / "jev_log.jsonl",
                      log=lambda *_: None)
    assert rep["primary"] == res["primary"]
    # a Jev that only knows income cannot add value over a logit that has income too
    assert res["primary"]["delta_log_loss_M4_minus_M1"] > -0.02
