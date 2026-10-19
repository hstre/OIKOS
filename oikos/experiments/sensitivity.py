"""One-at-a-time sensitivity: re-run the experiment under modified
assumptions and check whether the paired scenario effects keep their sign.

Structural alternatives (market protocol, number of trading partners,
population size) are treated like parameters, because they can matter as
much as parameter values.
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from ..config import deep_merge, load_experiment, load_yaml
from .runner import run_one, scenario_configs
from .summary import summarize_run


def _summarize(job):
    df, info = run_one(job[:3])
    s = summarize_run(df, info)
    s["variant"] = job[3]
    return s


def run_sensitivity(path: str | Path, out_dir: str | Path, n_seeds: int | None = None,
                    workers: int | None = None) -> Path:
    path = Path(path)
    spec = load_yaml(path)
    exp = load_experiment(path.parent / spec["experiment"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    first = int(spec["seeds"]["first"])
    seeds = range(first, first + int(n_seeds or spec["seeds"]["count"]))
    base_scen = scenario_configs(exp, include_control=False)

    jobs = []
    for variant, override in spec["variants"].items():
        for name, cfg in base_scen.items():
            vcfg = deep_merge(cfg, override or {})
            jobs += [(name, vcfg, s, variant) for s in seeds]

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_summarize, jobs, chunksize=4))
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "sensitivity_summary.csv", index=False)

    ref = exp["reference_scenario"]
    eff = []
    for (variant, sc), g in summary.groupby(["variant", "scenario"]):
        if sc == ref:
            continue
        r = summary[(summary.variant == variant) & (summary.scenario == ref)].set_index("seed")
        g = g.set_index("seed")
        for ind in spec["indicators"]:
            d = g[ind] - r.loc[g.index, ind]
            eff.append({"variant": variant, "scenario": sc, "indicator": ind, "median_diff": d.median(),
                        "q05": d.quantile(0.05), "q95": d.quantile(0.95)})
    eff = pd.DataFrame(eff)
    eff.to_csv(out / "sensitivity_effects.csv", index=False)
    _write_report(spec, eff, out, time.perf_counter() - t0, len(jobs))
    return out


def _sign(x: float, tol: float) -> int:
    return 0 if abs(x) <= tol else (1 if x > 0 else -1)


def _write_report(spec: dict, eff: pd.DataFrame, out: Path, seconds: float, runs: int) -> None:
    variants = list(spec["variants"])
    md = [f"# Sensitivität: {spec['name']}", "",
          f"{runs} Läufe, {seconds:.0f} s. Je Variante wird eine Annahme geändert; alle Szenarien und Seeds bleiben gleich.",
          "Zellen: Median der gepaarten Differenz Szenario − S0 über die Seeds. "
          "**fett** = Vorzeichen weicht von der Basisvariante ab (Toleranz: 5 % des Basisbetrags).", ""]
    for sc in sorted(eff.scenario.unique()):
        e = eff[eff.scenario == sc].pivot(index="variant", columns="indicator", values="median_diff")
        e = e.reindex(variants)[spec["indicators"]]
        base = e.loc["baseline"]
        md += [f"## {sc}", "", "| Variante | " + " | ".join(e.columns) + " |", "|---|" + "---|" * len(e.columns)]
        robust = {c: True for c in e.columns}
        for v, row in e.iterrows():
            cells = []
            for c in e.columns:
                tol = 0.05 * abs(base[c])
                flip = _sign(row[c], tol) != _sign(base[c], tol)
                if flip:
                    robust[c] = False
                txt = f"{row[c]:.4g}"
                cells.append(f"**{txt}**" if flip and v != "baseline" else txt)
            md.append(f"| {v} | " + " | ".join(cells) + " |")
        md += ["", "Vorzeichen robust über alle Varianten: " +
               ", ".join(f"{c}: {'ja' if ok else 'nein'}" for c, ok in robust.items()), ""]
    (out / "sensitivity.md").write_text("\n".join(md), encoding="utf-8")
