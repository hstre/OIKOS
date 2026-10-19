"""Robustness tests of the Jev budget question with simulated responses."""

import json
from pathlib import Path

import pytest

from oikos.behavior.jev.client import JevClient
from oikos.experiments import jev_robustness as jr

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "configs" / "experiments" / "jev_observe.yaml"
ORIG = ROOT / "results" / "jev_observe" / "jev_log.jsonl"


class FirstShownTransport:
    """Always picks the option listed first: a pure position effect."""

    def __init__(self, cost=0.00003):
        self.cost = cost
        self.n = 0

    def __call__(self, url, body, headers, timeout):
        self.n += 1
        req = json.loads(body)
        keys = list(req["questions"]["goods_budget"]["criteria"])
        probs = {k: (0.6 if i == 0 else 0.4 / (len(keys) - 1)) for i, k in enumerate(keys)}
        resp = {"model": "typesafe/jev-1.14-20261014", "provider": "TypeSafe", "id": "x",
                "answers": {"goods_budget": {"type": "choice", "choice": keys[0], "confidence": 0.3,
                                             "probabilities": probs}},
                "usage": {"input_tokens": 700, "output_tokens": 40, "cost": self.cost}}
        return 200, json.dumps(resp).encode()


def client(tr):
    return JevClient(api_key="sk-or-test", transport=tr, sleep=lambda s: None)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("rob")
    tr = FirstShownTransport()
    s = jr.run_tests(SPEC, ORIG, out, cost_limit_usd=0.01, client=client(tr), log=lambda *_: None)
    return s, out, tr


def test_same_48_states_are_reconstructed():
    states, _ = jr.reconstruct_states(SPEC, ORIG)
    assert len(states) == 48


def test_all_tests_run_within_cost_limit(run):
    s, _, tr = run
    assert tr.n == 240 and s["cost_usd_total"] <= 0.01
    for t in jr.TESTS:
        assert s["tests"][t]["requests_sent"] == 48 and s["tests"][t]["skipped_cost_limit"] == 0


def test_position_and_identifier_are_both_recorded(run):
    s, out, _ = run
    t1 = s["tests"]["T1_reversed_order"]
    assert t1["chosen_position_counts"] == {"1": 48}          # always first shown ...
    assert t1["chosen_key_counts"] == {"b5": 48}              # ... which is b5 in reversed order
    rows = [json.loads(x) for x in (out / "T1_reversed_order.jsonl").read_text().splitlines()]
    assert rows[0]["shown_order"] == ["b5", "b4", "b3", "b2", "b1"]


def test_comparisons_use_euro_budgets(run):
    s, _, _ = run
    # first shown in T5 is b1 (60 %), in T1 b5 (110 %): same scores structure, very different euro budgets
    assert s["tests"]["T5_repeat"]["chosen_share_of_base"]["median"] == pytest.approx(0.6, abs=0.02)
    assert s["tests"]["T1_reversed_order"]["chosen_share_of_base"]["median"] == pytest.approx(1.1, abs=0.03)
    assert s["tests"]["T4_wider_range"]["tvd_vs_original"]["n"] == 0  # different option sets: no TVD


def test_history_variant_is_labelled_synthetic(run):
    _, out, _ = run
    row = json.loads((out / "T3_with_history.jsonl").read_text().splitlines()[0])
    assert row["history_is_synthetic"] is True
    assert "synthetic" in row["request"]["state"]["history_note"]
    assert jr.HISTORY_FIELD in row["request"]["state"]["household"]


def test_cost_limit_skips_and_reports(tmp_path):
    tr = FirstShownTransport(cost=0.001)
    s = jr.run_tests(SPEC, ORIG, tmp_path, cost_limit_usd=0.01, client=client(tr), log=lambda *_: None)
    assert s["cost_usd_total"] <= 0.01
    skipped = sum(t["skipped_cost_limit"] for t in s["tests"].values())
    assert skipped > 0 and tr.n + skipped == 240


def test_replay_reproduces(run, tmp_path):
    s, out, _ = run
    r = jr.run_tests(SPEC, ORIG, tmp_path, mode="replay", replay_dir=out, log=lambda *_: None)
    for t in jr.TESTS:
        assert r["tests"][t]["chosen_key_counts"] == s["tests"][t]["chosen_key_counts"]
        assert r["tests"][t]["errors_by_kind"] == {}
