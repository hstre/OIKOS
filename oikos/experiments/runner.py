"""Run an experiment: every scenario with the same list of seeds (common
random numbers), in parallel, and store monthly records, per-run summaries
and a manifest that pins code, configuration and environment."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import config_hash, deep_merge, load_experiment
from ..model import Economy
from .summary import summarize_run


def scenario_configs(exp: dict, include_control: bool = True) -> dict[str, dict]:
    base = exp["base_config"]
    out = {name: deep_merge(base, ov or {}) for name, ov in exp["scenarios"].items()}
    if include_control:
        out.update({name: deep_merge(base, ov or {}) for name, ov in (exp.get("control") or {}).items()})
    return out


def run_one(args):
    scenario, cfg, seed = args
    t0 = time.perf_counter()
    eco = Economy(cfg, seed)
    records = eco.run()
    df = pd.DataFrame(records)
    df.insert(0, "seed", seed)
    df.insert(0, "scenario", scenario)
    info = {
        "scenario": scenario,
        "seed": seed,
        "seconds": time.perf_counter() - t0,
        "budget": eco.policy.budget,
        "flags": eco.flags,
        "cum": eco.cum,
        "decisions": eco.decision_stats(),
        "records_sha256": records_hash(records),
    }
    return df, info


def records_hash(records: list[dict]) -> str:
    blob = json.dumps(records, sort_keys=True, default=float).encode()
    return hashlib.sha256(blob).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parents[2]).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_experiment(path: str | Path, out_dir: str | Path, n_seeds: int | None = None,
                   workers: int | None = None) -> Path:
    exp = load_experiment(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    first = int(exp["seeds"]["first"])
    count = int(n_seeds if n_seeds is not None else exp["seeds"]["count"])
    seeds = list(range(first, first + count))
    configs = scenario_configs(exp)
    jobs = [(name, cfg, s) for name, cfg in configs.items() for s in seeds]

    t0 = time.perf_counter()
    workers = workers or max(1, (os.cpu_count() or 2))
    frames, infos = [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for df, info in pool.map(run_one, jobs, chunksize=4):
            frames.append(df)
            infos.append(info)
    wall = time.perf_counter() - t0

    monthly = pd.concat(frames, ignore_index=True)
    monthly.to_csv(out / "monthly.csv.gz", index=False, compression="gzip")
    summary = pd.DataFrame([summarize_run(df, info) for df, info in zip(frames, infos)])
    summary.to_csv(out / "summary.csv", index=False)

    # Replay check: re-run the first job and compare the record hash bit for bit.
    _, replay = run_one(jobs[0])
    replay_ok = replay["records_sha256"] == infos[0]["records_sha256"]

    manifest = {
        "experiment": exp["name"],
        "experiment_file": str(path),
        "created_unix": int(time.time()),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "platform": platform.platform(),
        "seeds": seeds,
        "reference_scenario": exp["reference_scenario"],
        "scenarios": {name: {"config_sha256_16": config_hash(cfg), "config": cfg} for name, cfg in configs.items()},
        "runs": len(jobs),
        "wall_seconds": round(wall, 1),
        "cpu_seconds_sum": round(sum(i["seconds"] for i in infos), 1),
        "workers": workers,
        "invariant_checks": "passed in every period of every run (a violation aborts the run)",
        "replay_check": {"job": [jobs[0][0], jobs[0][2]], "identical": replay_ok},
        "decision_models": _aggregate_decisions(infos),
        "run_flags": {k: int(sum(i["flags"][k] for i in infos)) for k in infos[0]["flags"]},
        "records_sha256": {f"{i['scenario']}/{i['seed']}": i["records_sha256"] for i in infos},
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    return out


def _aggregate_decisions(infos: list[dict]) -> dict:
    agg: dict[str, dict] = {}
    for info in infos:
        for name, d in info["decisions"].items():
            a = agg.setdefault(name, {k: d[k] for k in ("model", "version", "kind")} |
                               {"calls": 0, "agent_decisions": 0, "seconds": 0.0, "invalid_actions": 0})
            for k in ("calls", "agent_decisions", "seconds", "invalid_actions"):
                a[k] += d[k]
    for a in agg.values():
        a["seconds"] = round(a["seconds"], 2)
    return agg
