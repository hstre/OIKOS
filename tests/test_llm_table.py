import json
from pathlib import Path

import numpy as np
import pytest

from oikos.behavior.llm import household_table as ht
from oikos.behavior.llm.openrouter import Completion
from oikos.config import deep_merge, load_yaml
from oikos.model import Economy

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    """Answers deterministically from the prompt text; no network."""

    def __init__(self, bad_every: int = 0, cost: float = 0.001):
        self.calls = 0
        self.bad_every = bad_every
        self.cost = cost

    def complete(self, model, messages, **kw):
        self.calls += 1
        text = messages[1]["content"]
        if self.bad_every and self.calls % self.bad_every == 0:
            return Completion("not json", model + "-served", 10, 5, self.cost)
        e = -0.2 if "twice" in text else 0.0
        s = -0.1 if "less than one month" in text else 0.0
        body = json.dumps({"energy_use_change": e, "other_spending_change": s, "main_reason": "test"})
        return Completion(body, model + "-served", 100, 20, self.cost)


def test_cells_cover_shape_and_describe():
    assert ht.N_CELLS == 2 * 5 * 6 * 5 * 5
    d = ht.describe(ht.N_CELLS - 1)
    assert d["employment"] == "unemployed" and d["price"] == "more than twice"
    assert "{" not in ht.messages_for(0)[1]["content"]


def test_cells_of_maps_observations():
    obs = {"employed": np.array([1.0, 0.0]), "income_quintile": np.array([0.0, 4.0]),
           "energy_price": np.array([20.0, 9.0]), "reference_price": np.array([9.0, 9.0]),
           "need_kwh": np.array([1000.0, 1000.0]), "net_income": np.array([100000.0, 300000.0]),
           "wealth_before_income": np.array([50000.0, 5_000_000.0])}
    c = ht.cells_of(obs)
    assert ht.cell_coords(int(c[0])) == (0, 0, 5, 3, 0)   # price ratio 2.2, bill 20 % (15–25 %), savings 0.5 months
    assert ht.cell_coords(int(c[1])) == (1, 4, 1, 0, 4)


def test_build_table_is_resumable_and_records_costs(tmp_path):
    out = tmp_path / "t.json"
    client = FakeClient(bad_every=7)
    ht.build_table(client, "m", out, max_calls=50, concurrency=4, log=lambda *_: None)
    t = json.loads(out.read_text())
    assert len(t["cells"]) == 50 and t["meta"]["calls"] == 50
    assert t["meta"]["invalid"] == 7
    assert t["meta"]["models_answered"] == ["m-served"]
    assert (tmp_path / "t.csv").exists()
    ht.build_table(client, "m", out, max_calls=60, concurrency=4, log=lambda *_: None)
    assert len(json.loads(out.read_text())["cells"]) == 60 and client.calls == 60
    with pytest.raises(ValueError):
        ht.build_table(client, "other-model", out, log=lambda *_: None)


def test_cost_limit_stops_building(tmp_path):
    out = tmp_path / "t.json"
    ht.build_table(FakeClient(cost=0.5), "m", out, max_cost_usd=1.0, concurrency=1, log=lambda *_: None)
    t = json.loads(out.read_text())
    assert t["meta"]["stopped"].startswith("cost limit")
    assert len(t["cells"]) < ht.N_CELLS


def test_simulation_runs_with_table_model(tmp_path):
    out = tmp_path / "t.json"
    ht.build_table(FakeClient(), "m", out, concurrency=8, log=lambda *_: None)
    cfg = load_yaml(ROOT / "configs" / "baseline.yaml")
    cfg = deep_merge(cfg, {"simulation": {"burn_in_months": 12, "horizon_months": 12},
                           "households": {"n": 200}, "firms": {"n": 5},
                           "behavior": {"household": {"model": "llm_table", "table": str(out)}}})
    eco = Economy(cfg, 1)
    eco.run()
    model = eco.household_model.model
    assert model.meta.kind == "llm" and model.lookups == 200 * 24 and model.fallbacks == 0
    assert eco.decision_stats()["household_model"]["model"] == "household_llm_table"
