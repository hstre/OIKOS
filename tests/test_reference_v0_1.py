"""v0.1 is the frozen reference. These tests fail if any change alters the
results of the rule-based model: they recompute runs of experiment 1 and
compare them bit for bit with the hashes stored in its manifest."""

import json
from pathlib import Path

import pytest

from oikos.config import load_experiment
from oikos.experiments.runner import run_one, scenario_configs

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "results" / "energy_shock" / "manifest.json").read_text())


@pytest.mark.parametrize("scenario,seed", [("S0_none", 1), ("S2_subsidy", 7), ("S3_investment", 42)])
def test_rule_model_reproduces_v0_1_results(scenario, seed):
    exp = load_experiment(ROOT / "configs" / "experiments" / "energy_shock.yaml")
    cfg = scenario_configs(exp)[scenario]
    _, info = run_one((scenario, cfg, seed))
    assert info["records_sha256"] == MANIFEST["records_sha256"][f"{scenario}/{seed}"]
