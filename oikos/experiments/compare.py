"""Compare scenario effects between two experiment directories, e.g. the
rule-based household model against an LLM-derived decision table. Effects
are paired differences to the reference scenario within each experiment;
the comparison is between effect distributions, not between single runs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .report import paired_differences
from .summary import INDICATORS


def compare(dir_a: str | Path, dir_b: str | Path, out: str | Path | None = None) -> Path:
    a, b = Path(dir_a), Path(dir_b)
    ref = json.loads((a / "manifest.json").read_text())["reference_scenario"]
    da = paired_differences(pd.read_csv(a / "summary.csv").query("scenario.str.startswith('S')"), ref)
    db = paired_differences(pd.read_csv(b / "summary.csv").query("scenario.str.startswith('S')"), ref)
    m = da.merge(db, on=["scenario", "indicator"], suffixes=("_a", "_b"))
    out = Path(out) if out else b / f"compare_with_{a.name}.md"
    md = [f"# Vergleich der Szenario-Effekte: `{a.name}` (A) gegen `{b.name}` (B)", "",
          "Median der gepaarten Differenz zu " + ref + " mit 5–95 %-Spanne über die Seeds. "
          "Vorzeichenwechsel zwischen A und B sind markiert (!).", ""]
    for sc in sorted(m.scenario.unique()):
        md += [f"## {sc}", "", "| Indikator | A Median | A Spanne | B Median | B Spanne | |", "|---|---|---|---|---|---|"]
        for _, r in m[m.scenario == sc].iterrows():
            if r.indicator not in INDICATORS:
                continue
            flip = "!" if (r.median_a > 0) != (r.median_b > 0) and abs(r.median_a) > 1e-9 and abs(r.median_b) > 1e-9 else ""
            md.append(f"| {r.indicator} | {r.median_a:.4g} | {r.q05_a:.3g} … {r.q95_a:.3g} | "
                      f"{r.median_b:.4g} | {r.q05_b:.3g} … {r.q95_b:.3g} | {flip} |")
        md.append("")
    out.write_text("\n".join(md), encoding="utf-8")
    return out
