"""v0.1 is the frozen reference.

Two levels:
1. Everywhere: the per-run indicators of experiment 1 are recomputed and
   compared with the committed results/energy_shock/summary.csv (integer
   quantities exactly, floating-point quantities with relative tolerance 1e-9).
2. On hardware like the one that produced v0.1 (numpy dispatching to x86-64-v4 /
   AVX-512 kernels): bit-for-bit identity with the record hashes in the manifest.
   numpy's SIMD kernels for exp/log etc. may differ in the last bit between CPU
   instruction sets, so bitwise identity across different hardware is not
   guaranteed (observed: relative differences around 1e-15 without AVX-512).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from oikos.config import load_experiment
from oikos.experiments.runner import cpu_features, run_one, scenario_configs
from oikos.experiments.summary import summarize_run

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "results" / "energy_shock" / "manifest.json").read_text())
SUMMARY = pd.read_csv(ROOT / "results" / "energy_shock" / "summary.csv")
CASES = [("S0_none", 1), ("S2_subsidy", 7), ("S3_investment", 42)]
INTEGER = {"firm_exits", "retrofits", "seed"}


def _run(scenario, seed):
    exp = load_experiment(ROOT / "configs" / "experiments" / "energy_shock.yaml")
    df, info = run_one((scenario, scenario_configs(exp)[scenario], seed))
    return df, info


@pytest.mark.parametrize("scenario,seed", CASES)
def test_rule_model_matches_v0_1_indicators(scenario, seed):
    df, info = _run(scenario, seed)
    got = summarize_run(df, info)
    ref = SUMMARY[(SUMMARY.scenario == scenario) & (SUMMARY.seed == seed)].iloc[0]
    for k, v in got.items():
        if k == "scenario":
            continue
        if k in INTEGER:
            assert v == ref[k], k
        else:
            assert np.isclose(v, ref[k], rtol=1e-9, atol=1e-12, equal_nan=True), (k, v, ref[k])


@pytest.mark.skipif(not cpu_features().get("X86_V4", False),
                    reason="bitwise v0.1 reference was recorded with numpy x86-64-v4 (AVX-512) kernels")
@pytest.mark.parametrize("scenario,seed", CASES)
def test_rule_model_reproduces_v0_1_bitwise(scenario, seed):
    _, info = _run(scenario, seed)
    assert info["records_sha256"] == MANIFEST["records_sha256"][f"{scenario}/{seed}"]
