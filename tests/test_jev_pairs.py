"""Paired Jev test with simulated responses."""

import json
from pathlib import Path

import pytest

from oikos.behavior.jev.client import JevClient
from oikos.config import load_yaml
from oikos.experiments import jev_pairs as jp

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "configs" / "experiments" / "jev_pairs.yaml"


def fake(pick):
    """Transport whose answer is computed by pick(household, shown_codes, amount_of) -> scores."""
    spec = load_yaml(SPEC)
    amounts = spec["options_eur"]

    def transport(url, body, headers, timeout):
        req = json.loads(body)
        crit = req["questions"]["goods_budget"]["criteria"]
        shown = list(crit)
        amount_of = {k: int(v.split()[2]) for k, v in crit.items()}
        scores = pick(req["state"]["household"], shown, amount_of)
        choice = max(scores, key=scores.get)
        resp = {"model": "typesafe/jev-1.14-20261014", "provider": "TypeSafe", "id": "x",
                "answers": {"goods_budget": {"type": "choice", "choice": choice, "confidence": 0.3,
                                             "probabilities": scores}},
                "usage": {"input_tokens": 500, "output_tokens": 40, "cost": 0.00002}}
        return 200, json.dumps(resp).encode()

    assert amounts == [1200, 1500, 1800, 2100, 2400]
    return JevClient(api_key="sk-or-test", transport=transport, sleep=lambda s: None)


def by_amount(amount_of, weights):
    s = {k: weights[amount_of[k]] for k in amount_of}
    tot = sum(s.values())
    return {k: v / tot for k, v in s.items()}


def test_design_is_balanced_and_affordable():
    spec = load_yaml(SPEC)
    n = len(spec["options_eur"])
    positions = {a: set() for a in range(n)}
    codes = {a: set() for a in range(n)}
    for j in range(spec["presentations"]["count"]):
        order, code = jp.presentation(spec, j)
        assert sorted(order) == list(range(n)) and len(set(code.values())) == n
        for pos, a in enumerate(order):
            positions[a].add(pos)
            codes[a].add(code[a])
    assert all(len(p) == n for p in positions.values())   # each amount once at each position
    assert all(len(c) == n for c in codes.values())       # each amount once with each identifier
    for p in spec["pairs"].values():
        for case in ("A", "B"):
            hh = jp.household(spec, p[case])
            assert hh["money_available_after_energy_bill_eur"] >= max(spec["options_eur"])


def test_pair_cases_differ_in_exactly_one_feature():
    spec = load_yaml(SPEC)
    derived = {"money_available_after_energy_bill_eur"}
    for name, p in spec["pairs"].items():
        a, b = jp.household(spec, p["A"]), jp.household(spec, p["B"])
        diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)} - derived
        if name == "P4_energy_price":   # price and resulting bill are one economic fact
            assert diff == {"energy_price_now_ct_per_kwh", "energy_bill_this_month_eur"}
        else:
            assert len(diff) == 1, (name, diff)


def test_request_count_and_cost_within_limits(tmp_path):
    s = jp.run_pairs(SPEC, tmp_path, client=fake(lambda h, sh, am: by_amount(am, {a: 1 for a in am.values()})),
                     log=lambda *_: None)
    assert s["requests"] == 72 and s["requests_ok"] == 72 and s["cost_usd_total"] <= 0.01


def test_pure_position_bias_is_not_read_as_information(tmp_path):
    # always favours the first shown option, regardless of the household
    def pick(h, shown, am):
        return {k: (0.6 if i == 0 else 0.1) for i, k in enumerate(shown)}
    s = jp.run_pairs(SPEC, tmp_path, client=fake(pick), log=lambda *_: None)
    for p in s["pairs"].values():
        assert p["median_delta_weighted_eur"] == pytest.approx(0.0)
        assert not p["consistently_distinguished"]


def test_genuine_information_response_is_detected(tmp_path):
    # favours low budgets only when job outlook is uncertain; mild position bias on top
    def pick(h, shown, am):
        low = "uncertain" in str(h.get("job_outlook", ""))
        w = {1200: 4 if low else 1, 1500: 3 if low else 1, 1800: 2, 2100: 1 if low else 3, 2400: 1 if low else 3}
        s = {k: w[am[k]] * (1.3 if i == 0 else 1.0) for i, k in enumerate(shown)}
        tot = sum(s.values())
        return {k: v / tot for k, v in s.items()}
    s = jp.run_pairs(SPEC, tmp_path, client=fake(pick), log=lambda *_: None)
    p1 = s["pairs"]["P1_job_security"]
    assert p1["direction"] == "lower" and p1["same_sign_presentations"] == 5
    assert s["pairs"]["P0_placebo"]["median_delta_weighted_eur"] == pytest.approx(0.0)


def test_replay_reproduces(tmp_path):
    c = fake(lambda h, sh, am: by_amount(am, {1200: 1, 1500: 2, 1800: 3, 2100: 2, 2400: 1}))
    live = jp.run_pairs(SPEC, tmp_path / "live", client=c, log=lambda *_: None)
    rep = jp.run_pairs(SPEC, tmp_path / "rep", mode="replay", replay_log=tmp_path / "live" / "jev_log.jsonl",
                       log=lambda *_: None)
    assert rep["requests_ok"] == 72
    assert {k: v["median_delta_weighted_eur"] for k, v in rep["pairs"].items()} == \
           {k: v["median_delta_weighted_eur"] for k, v in live["pairs"].items()}
