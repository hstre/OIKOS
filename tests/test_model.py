from pathlib import Path

import numpy as np
import pytest

from oikos.config import deep_merge, load_yaml
from oikos.experiments.runner import records_hash
from oikos.model import Economy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def small_cfg():
    cfg = load_yaml(ROOT / "configs" / "baseline.yaml")
    return deep_merge(cfg, {
        "simulation": {"burn_in_months": 24, "horizon_months": 30},
        "households": {"n": 300},
        "firms": {"n": 8},
    })


def run(cfg, seed=3, **override):
    eco = Economy(deep_merge(cfg, override), seed)
    eco.run()  # invariants are checked inside every period
    return eco


def test_runs_with_all_invariants(small_cfg):
    eco = run(small_cfg)
    assert len(eco.records) == 54
    assert eco.flags["bank_negative_equity_months"] == 0


def test_same_seed_is_bitwise_reproducible(small_cfg):
    assert records_hash(run(small_cfg).records) == records_hash(run(small_cfg).records)


def test_different_seeds_differ(small_cfg):
    assert records_hash(run(small_cfg, seed=3).records) != records_hash(run(small_cfg, seed=4).records)


@pytest.mark.parametrize("instrument", ["transfer", "subsidy", "investment"])
def test_common_random_numbers_until_policy_start(small_cfg, instrument):
    a = run(small_cfg, policy={"instrument": "none"})
    b = run(small_cfg, policy={"instrument": instrument})
    pre_a = [r for r in a.records if r["t"] < 0]
    pre_b = [r for r in b.records if r["t"] < 0]
    assert records_hash(pre_a) == records_hash(pre_b)
    assert a.policy.budget == b.policy.budget > 0


def test_transfer_pays_exactly_its_budget_share(small_cfg):
    eco = run(small_cfg, policy={"instrument": "transfer"})
    per_hh = eco.policy.budget // (eco.policy.duration * eco.H)
    assert eco.cum["policy_cost"] == per_hh * eco.H * eco.policy.duration


def test_subsidy_lowers_household_price_only_during_programme(small_cfg):
    base = run(small_cfg, policy={"instrument": "none"})
    sub = run(small_cfg, policy={"instrument": "subsidy"})
    during = [r["hh_energy_price_ct_kwh"] for r in sub.records if 0 <= r["t"] < 24]
    during0 = [r["hh_energy_price_ct_kwh"] for r in base.records if 0 <= r["t"] < 24]
    assert np.all(np.array(during) < np.array(during0))
    assert sub.cum["policy_cost"] > 0


def test_investment_retrofits_reduce_energy_need(small_cfg):
    eco = run(small_cfg, policy={"instrument": "investment"})
    assert eco.cum["retrofits"] > 0
    done = eco.retrofitted & (eco.retrofit_at <= eco.t_end - 1)
    np.testing.assert_allclose(eco.efficiency[done], 1 - eco.policy.need_reduction)


def test_random_queue_protocol_runs(small_cfg):
    run(small_cfg, institutions={"goods_market_protocol": "random_queue"})


def test_unknown_override_key_is_rejected(small_cfg):
    with pytest.raises(KeyError):
        deep_merge(small_cfg, {"households": {"typo": 1}})
