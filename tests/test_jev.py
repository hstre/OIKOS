"""Jev adapter with simulated API responses (no network, no costs)."""

import json
import urllib.error
from pathlib import Path

import numpy as np
import pytest
import yaml

from oikos.behavior.jev import household_budget as hb
from oikos.behavior.jev.client import (JevClient, MissingKeyError, ReplayClient, request_hash)
from oikos.behavior.protocol import Box, Decider, DecisionShapeError, ModelMeta
from oikos.experiments.jev_observe import ping, run_observation

ROOT = Path(__file__).resolve().parents[1]
FAKE_KEY = "sk-or-v1-TEST-SECRET-0123456789"
FRACTIONS = [0.6, 0.75, 0.9, 1.0, 1.1]


def answer(choice="b3", probs=None, **extra):
    probs = probs if probs is not None else {"b1": 0.05, "b2": 0.15, "b3": 0.5, "b4": 0.25, "b5": 0.05}
    a = {"type": "choice", "choice": choice, "confidence": 0.4, "probabilities": probs, **extra}
    return {"id": "gen-dec-test", "model": "typesafe/jev-1.14-20261014", "provider": "TypeSafe",
            "answers": {"goods_budget": a}, "usage": {"input_tokens": 420, "output_tokens": 30, "cost": 0.0000176}}


class FakeTransport:
    """Records what was sent; replies with a fixed payload or a sequence of outcomes."""

    def __init__(self, outcomes=None, payload=None):
        self.outcomes = list(outcomes or [])
        self.payload = payload or answer()
        self.sent = []

    def __call__(self, url, body, headers, timeout):
        self.sent.append((url, json.loads(body), dict(headers)))
        if self.outcomes:
            o = self.outcomes.pop(0)
            if isinstance(o, Exception):
                raise o
            return o
        return 200, json.dumps(self.payload).encode()


def client(transport, **kw):
    return JevClient(api_key=FAKE_KEY, transport=transport, sleep=lambda s: None, **kw)


def body():
    b, _ = hb.build_request("typesafe/jev-1.14", employed=True, net_income=240_000, savings=800_000,
                            deposits=1_020_000, price_now=16.2, price_usual=9.0, energy_cost=19_000,
                            fractions=FRACTIONS)
    return b


# ------------------------------------------------------------------ client
def test_missing_key_is_an_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(MissingKeyError):
        JevClient()
    monkeypatch.setenv("OPENROUTER_API_KEY", "   ")
    with pytest.raises(MissingKeyError):
        JevClient()


def test_key_only_in_authorization_header(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    tr = FakeTransport()
    rec = JevClient(transport=tr).decide(body())
    url, sent_body, headers = tr.sent[0]
    assert url == "https://openrouter.ai/api/alpha/decisions"
    assert headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert FAKE_KEY not in json.dumps(sent_body)
    assert FAKE_KEY not in json.dumps(rec.to_dict())
    assert FAKE_KEY not in repr(JevClient(transport=tr))


def test_successful_call_records_model_tokens_cost():
    rec = client(FakeTransport()).decide(body())
    assert rec.status == "ok" and rec.model_served == "typesafe/jev-1.14-20261014"
    assert rec.input_tokens == 420 and rec.cost_usd == pytest.approx(0.0000176)
    assert rec.request_sha256 == request_hash(body())


def test_connection_error_is_retried_then_reported_and_redacted():
    err = urllib.error.URLError(f"refused for key {FAKE_KEY}")
    rec = client(FakeTransport(outcomes=[err, err, err]), retries=2).decide(body())
    assert rec.status == "error" and rec.error_kind == "connection" and rec.attempts == 3
    assert FAKE_KEY not in rec.error and "[REDACTED]" in rec.error


def test_retry_recovers_after_transient_error():
    rec = client(FakeTransport(outcomes=[(503, b'{"error":{"message":"overloaded"}}')])).decide(body())
    assert rec.status == "ok" and rec.attempts == 2


def test_auth_error_is_not_retried():
    tr = FakeTransport(outcomes=[(401, b'{"error":{"code":401,"message":"bad key"}}')])
    rec = client(tr).decide(body())
    assert rec.status == "error" and rec.error_kind == "http_status" and rec.http_status == 401
    assert rec.attempts == 1 and "bad key" in rec.error


def test_non_json_response_is_an_error():
    rec = client(FakeTransport(outcomes=[(200, b"<html>")])).decide(body())
    assert rec.status == "error" and rec.error_kind == "response_format"


# --------------------------------------------------------------- parsing
KEYS = ["b1", "b2", "b3", "b4", "b5"]


@pytest.mark.parametrize("response,kind", [
    ({}, "response_format"),                                                     # no answers
    ({"answers": {}}, "response_format"),                                        # empty answers
    ({"answers": {"goods_budget": {"type": "choice", "probabilities": {}}}}, "response_format"),  # no choice
    ({"answers": {"goods_budget": {"type": "noul", "noul": 0.3}}}, "response_format"),            # wrong type
    (answer(probs=None) | {"answers": {"goods_budget": {"type": "choice", "choice": "b1"}}}, "response_format"),
    (answer(probs={"b1": 0.5, "b2": 0.5, "b3": 0, "b4": 0}), "response_format"),            # 4 of 5 options
    (answer(probs={k: 0.2 for k in KEYS} | {"b6": 0.0}), "response_format"),                # 6 entries
    (answer(probs={"b1": 1.5, "b2": -0.5, "b3": 0, "b4": 0, "b5": 0}), "response_format"),  # out of range
    (answer(probs={k: 0.5 for k in KEYS}), "response_format"),                              # sums to 2.5
    (answer(choice="b9"), "invalid_action"),                                                # not an option
    (answer(choice="spend everything"), "invalid_action"),
])
def test_malformed_answers_are_rejected(response, kind):
    with pytest.raises(Exception) as e:
        hb.parse_choice(response, KEYS)
    assert e.value.kind == kind


def test_extra_answers_are_rejected():
    r = answer()
    r["answers"]["other"] = {"type": "noul", "noul": 0.5}
    with pytest.raises(Exception) as e:
        hb.parse_choice(r, KEYS)
    assert e.value.kind == "response_format"


def test_valid_answer_is_parsed():
    choice, probs, conf = hb.parse_choice(answer(), KEYS)
    assert choice == "b3" and probs["b3"] == 0.5 and conf == 0.4


# --------------------------------------------------------------- request
def test_request_contains_only_household_knowledge():
    b = body()
    hh = b["state"]["household"]
    assert set(hh) == {"employment", "net_income_this_month_eur", "savings_before_this_months_income_eur",
                       "energy_price_now_ct_per_kwh", "energy_price_usually_paid_ct_per_kwh",
                       "energy_bill_this_month_eur", "money_available_after_energy_bill_eur"}
    text = json.dumps(b).lower()
    for forbidden in ("quintile", "propensit", "c_income", "c_wealth", "elasticity", "unemployment rate",
                      "price index", "other households"):
        assert forbidden not in text
    q = b["questions"]["goods_budget"]
    assert q["type"] == "choice" and list(q["criteria"]) == KEYS


def test_options_ascending_rounded_and_capped():
    opts = hb.budget_options(net_income=240_000, energy_cost=19_000, deposits=150_000, fractions=FRACTIONS)
    vals = list(opts.values())
    assert vals == sorted(vals) and all(v % 1000 == 0 for v in vals)
    assert max(vals) <= 150_000 - 19_000 + 1000  # never more than available (up to rounding)


# --------------------------------------------------------- observation runs
def small_spec(tmp_path, **jev_over):
    spec = yaml.safe_load((ROOT / "configs" / "experiments" / "jev_observe.yaml").read_text())
    spec["base"] = str(ROOT / "configs" / "baseline.yaml")
    spec["scenario"] = {"policy": {"instrument": "none"}, "households": {"n": 200}, "firms": {"n": 5},
                        "simulation": {"burn_in_months": 12, "horizon_months": 36}}
    spec["out"] = str(tmp_path / "out")
    spec["jev"].update(jev_over)
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.safe_dump(spec))
    return p


def test_observation_logs_decisions_without_changing_the_economy(tmp_path):
    spec = small_spec(tmp_path)
    s = run_observation(spec, client=client(FakeTransport()), log=lambda *_: None)
    assert s["requests"] == 48 and s["ok"] == 48 and s["errors"] == 0
    assert s["economy_unchanged_by_observation"] is True
    assert s["models_served"] == ["typesafe/jev-1.14-20261014"]
    assert s["cost_usd_total"] == pytest.approx(48 * 0.0000176)
    lines = (tmp_path / "out" / "jev_log.jsonl").read_text().splitlines()
    assert len(lines) == 48
    row = json.loads(lines[0])
    assert row["probability_semantics"] == "score"
    assert {"request", "response", "model_served", "rule_budget_cents", "jev_choice"} <= set(row)


def test_errors_are_logged_not_replaced_by_rule(tmp_path):
    spec = small_spec(tmp_path, months=[-1], households_per_month=6)
    outcomes = [(200, json.dumps(answer(choice="b9")).encode()),          # invalid action
                (200, json.dumps({"model": "x", "usage": {}}).encode()),  # answers missing
                (400, b'{"error":{"message":"bad request"}}'),
                urllib.error.URLError("down"), urllib.error.URLError("down"), urllib.error.URLError("down")]
    s = run_observation(spec, client=client(FakeTransport(outcomes=outcomes), retries=2), log=lambda *_: None)
    # 1 invalid action, 1 missing answers, 1 HTTP 400, 1 connection failure (3 attempts); 2 ok
    assert s["requests"] == 6 and s["errors"] == 4 and s["ok"] == 2
    assert s["errors_by_kind"] == {"invalid_action": 1, "response_format": 1, "http_status": 1, "connection": 1}
    rows = [json.loads(x) for x in (tmp_path / "out" / "jev_log.jsonl").read_text().splitlines()]
    bad = [r for r in rows if r["status"] == "error"]
    assert {r["error_kind"] for r in bad} == {"invalid_action", "response_format", "http_status", "connection"}
    for r in bad:
        assert "jev_choice" not in r and "jev_budget_cents" not in r   # no substitute decision


def test_decision_limit_is_enforced(tmp_path):
    with pytest.raises(ValueError):
        run_observation(small_spec(tmp_path, max_decisions=51), client=client(FakeTransport()))
    with pytest.raises(ValueError):
        run_observation(small_spec(tmp_path, households_per_month=13), client=client(FakeTransport()))


def test_replay_reproduces_without_network(tmp_path):
    spec = small_spec(tmp_path)
    live = run_observation(spec, client=client(FakeTransport()), log=lambda *_: None)
    log = tmp_path / "out" / "jev_log.jsonl"
    replay = run_observation(spec, out_dir=tmp_path / "replay", mode="replay", replay_log=log, log=lambda *_: None)
    assert replay["replayed"] is True and replay["errors"] == 0
    for k in ("same_option_as_rule_share", "option_steps_vs_rule", "cost_usd_total", "models_served"):
        assert replay[k] == live[k]
    a = [json.loads(x) for x in log.read_text().splitlines()]
    b = [json.loads(x) for x in (tmp_path / "replay" / "jev_log.jsonl").read_text().splitlines()]
    assert [r["jev_choice"] for r in a] == [r["jev_choice"] for r in b]


def test_replay_miss_is_an_error(tmp_path):
    log = tmp_path / "empty.jsonl"
    log.write_text("")
    rec = ReplayClient(log).decide(body())
    assert rec.status == "error" and rec.error_kind == "replay_miss"


def test_no_credentials_in_any_output(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    spec = small_spec(tmp_path)
    run_observation(spec, client=JevClient(transport=FakeTransport(), sleep=lambda s: None), log=lambda *_: None)
    ping(spec, tmp_path / "out" / "ping.json", client=JevClient(transport=FakeTransport()))
    for f in (tmp_path / "out").iterdir():
        assert FAKE_KEY not in f.read_text(encoding="utf-8"), f.name
        assert "Bearer" not in f.read_text(encoding="utf-8"), f.name


# ------------------------------------------------- decision interface shapes
def test_decider_rejects_wrong_array_length_and_missing_actions():
    class Short:
        meta = ModelMeta("short", "0", "rule", True)

        def decide(self, obs, space, rng):
            return {"x": np.array([0.5])}  # would silently broadcast to all agents

    class Missing:
        meta = ModelMeta("missing", "0", "rule", True)

        def decide(self, obs, space, rng):
            return {}

    obs, space, rng = {"a": np.zeros(4)}, {"x": Box(0.0, 1.0)}, np.random.default_rng(0)
    with pytest.raises(DecisionShapeError):
        Decider(Short())(obs, space, rng)
    with pytest.raises(DecisionShapeError):
        Decider(Missing())(obs, space, rng)
