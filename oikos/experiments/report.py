"""Generate a Markdown report with tables and figures from an experiment
directory (monthly.csv.gz, summary.csv, manifest.json)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .summary import INDICATORS

# Reference categorical palette (light), fixed order, validated adjacent pairs.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

LABELS = {
    "S0_none": "S0 keine Maßnahme",
    "S1_transfer": "S1 Transfer",
    "S2_subsidy": "S2 Preissubvention",
    "S3_investment": "S3 Effizienzinvestition",
    "C0_no_shock": "C0 ohne Schock",
}

SERIES_PLOTS = [
    ("unemployment", "Arbeitslosenquote", 100, "%"),
    ("real_consumption", "Realer Konsum der Haushalte", 1e-3, "Tsd. Einheiten/Monat"),
    ("q1_real_consumption", "Realer Konsum, unterstes Quintil", 1, "Einheiten/Haushalt"),
    ("energy_burden_share", "Haushalte mit Energieausgaben > 10 % des Einkommens", 100, "%"),
    ("energy_imports_kwh", "Importierte Primärenergie", 1e-6, "GWh/Monat"),
    ("gov_debt", "Staatsschuld (netto)", 1e-8, "Mio. €"),
]


def _quantiles(x: pd.Series) -> tuple[float, float, float]:
    return float(x.quantile(0.05)), float(x.median()), float(x.quantile(0.95))


def _fmt(v: float) -> str:
    if not np.isfinite(v):
        return "–"
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 100:
        return f"{v:,.0f}".replace(",", " ")
    if a >= 1:
        return f"{v:.2f}"
    return f"{v:.4f}"


def _style(ax, title: str, unit: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_ylabel(unit, fontsize=8, color=INK_2)
    ax.tick_params(colors=INK_2, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.axvspan(0, 24, color="#000000", alpha=0.035, linewidth=0)


def make_figures(monthly: pd.DataFrame, scenarios: list[str], out: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    files = []
    window = monthly[monthly.t >= -12]
    fig, axes = plt.subplots(3, 2, figsize=(11, 10.5), facecolor=SURFACE)
    for ax, (col, title, scale, unit) in zip(axes.flat, SERIES_PLOTS):
        for i, sc in enumerate(scenarios):
            d = window[window.scenario == sc].groupby("t")[col]
            q05, q50, q95 = (d.quantile(q) * scale for q in (0.05, 0.5, 0.95))
            ax.fill_between(q50.index, q05, q95, color=SERIES[i], alpha=0.13, linewidth=0)
            ax.plot(q50.index, q50, color=SERIES[i], linewidth=2, label=LABELS.get(sc, sc))
        _style(ax, title, unit)
        ax.set_xlabel("Monat (0 = Schockbeginn, grau = Schockphase)", fontsize=8, color=INK_2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(scenarios), frameon=False, fontsize=9)
    fig.text(0.01, 0.005, "Linie: Median über alle Zufallsstarts; Band: 5–95 %-Quantil.", fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.01, 1, 0.96))
    fig.savefig(out / "fig_paths.png", dpi=130)
    plt.close(fig)
    files.append("fig_paths.png")

    # Individual paths: distributions hide that single runs can look very different.
    fig, axes = plt.subplots(1, len(scenarios), figsize=(11, 3), sharey=True, facecolor=SURFACE)
    seeds = sorted(window.seed.unique())[:8]
    for i, (ax, sc) in enumerate(zip(np.atleast_1d(axes), scenarios)):
        for s in seeds:
            d = window[(window.scenario == sc) & (window.seed == s)]
            ax.plot(d.t, d.unemployment * 100, color=SERIES[i], linewidth=1, alpha=0.7)
        _style(ax, LABELS.get(sc, sc), "%" if i == 0 else "")
    fig.suptitle(f"Arbeitslosenquote: einzelne Läufe (Seeds {seeds[0]}–{seeds[-1]})", x=0.01, ha="left",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig_single_runs.png", dpi=130)
    plt.close(fig)
    files.append("fig_single_runs.png")
    return files


def paired_differences(summary: pd.DataFrame, reference: str) -> pd.DataFrame:
    ref = summary[summary.scenario == reference].set_index("seed")
    rows = []
    for sc in summary.scenario.unique():
        if sc == reference:
            continue
        cur = summary[summary.scenario == sc].set_index("seed")
        common = cur.index.intersection(ref.index)
        for ind in INDICATORS:
            diff = cur.loc[common, ind] - ref.loc[common, ind]
            q05, q50, q95 = _quantiles(diff)
            rows.append({"scenario": sc, "indicator": ind, "q05": q05, "median": q50, "q95": q95,
                         "share_positive": float((diff > 0).mean()), "n": int(diff.size)})
    return pd.DataFrame(rows)


def mechanism_checks(summary: pd.DataFrame) -> list[tuple[str, str, float]]:
    s = {sc: g.set_index("seed") for sc, g in summary.groupby("scenario")}
    if not {"S0_none", "S1_transfer", "S2_subsidy", "S3_investment"} <= s.keys():
        return []
    s0, s1, s2, s3 = s["S0_none"], s["S1_transfer"], s["S2_subsidy"], s["S3_investment"]
    share = lambda m: float(m.mean())  # noqa: E731
    return [
        ("E1", "Subvention: höhere Energieimporte als Transfer (Monate 0–23)",
         share(s2.energy_imports_shock > s1.energy_imports_shock)),
        ("E2", "Transfer: höherer realer Konsum im untersten Quintil als Subvention (0–23)",
         share(s1.q1_real_consumption_shock > s2.q1_real_consumption_shock)),
        ("E2b", "Transfer: geringerer Anteil Energiekostenbelastung > 10 % im untersten Quintil als Subvention",
         share(s1.q1_energy_burden_shock < s2.q1_energy_burden_shock)),
        ("E3a", "Investition: geringere Energieimporte als S0 nach Monat 24",
         share(s3.energy_imports_after < s0.energy_imports_after)),
        ("E3b", "Investition: geringere Energieimporte als Transfer nach Monat 24",
         share(s3.energy_imports_after < s1.energy_imports_after)),
        ("E3c", "Investition: kurzfristig schwächere Entlastung Q1 als Transfer (realer Konsum 0–23)",
         share(s3.q1_real_consumption_shock < s1.q1_real_consumption_shock)),
    ]


def stationarity(monthly: pd.DataFrame, control: str) -> pd.DataFrame:
    c = monthly[monthly.scenario == control]
    early = c[(c.t >= -12) & (c.t < 0)].groupby("seed").mean(numeric_only=True)
    late = c[(c.t >= 48) & (c.t < 60)].groupby("seed").mean(numeric_only=True)
    rows = []
    for col, kind in [("unemployment", "abs"), ("price_index", "rel"), ("avg_wage", "rel"),
                      ("money_stock", "rel"), ("real_consumption", "rel")]:
        d = late[col] - early[col] if kind == "abs" else late[col] / early[col] - 1
        q05, q50, q95 = _quantiles(d)
        rows.append({"Größe": col, "Maß": "Differenz (Pp./100)" if kind == "abs" else "relative Änderung",
                     "q05": q05, "Median": q50, "q95": q95})
    return pd.DataFrame(rows)


def profile_status(profile_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in sorted(profile_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        for p in data.get("parameters", []):
            counts[p["status"]] = counts.get(p["status"], 0) + 1
    return counts


def _table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(_fmt(v) if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |")
    return "\n".join(lines)


def build_report(exp_dir: str | Path, profile_dir: str | Path = "profiles") -> Path:
    out = Path(exp_dir)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    summary = pd.read_csv(out / "summary.csv")
    monthly = pd.read_csv(out / "monthly.csv.gz")
    reference = manifest["reference_scenario"]
    main = [s for s in manifest["scenarios"] if s.startswith("S")]
    control = [s for s in manifest["scenarios"] if s.startswith("C")]
    figs = make_figures(monthly, main, out)

    levels = []
    for sc in main:
        g = summary[summary.scenario == sc]
        for ind, (desc, unit) in INDICATORS.items():
            q05, q50, q95 = _quantiles(g[ind])
            levels.append({"Szenario": sc, "Indikator": ind, "q05": q05, "Median": q50, "q95": q95})
    levels = pd.DataFrame(levels)
    wide = levels.pivot(index="Indikator", columns="Szenario", values="Median").reindex(list(INDICATORS))
    wide.insert(0, "Einheit", [INDICATORS[i][1] for i in wide.index])
    wide.insert(0, "Beschreibung", [INDICATORS[i][0] for i in wide.index])

    diffs = paired_differences(summary[summary.scenario.isin(main)], reference)
    diffs.to_csv(out / "paired_differences.csv", index=False)
    checks = mechanism_checks(summary)
    stat = stationarity(monthly, control[0]) if control else None
    status = profile_status(Path(profile_dir))
    budget = summary[summary.scenario == "S1_transfer"].budget

    md = [f"# Experiment: {manifest['experiment']}", ""]
    md += [
        "**Bedingte Aussage.** Alle Ergebnisse gelten nur innerhalb dieses stilisierten Modells mit "
        "seinen gesetzten, nicht kalibrierten Parametern und Verhaltensregeln. Sie sind keine Prognose.",
        "",
        f"- Läufe: {manifest['runs']} ({len(manifest['seeds'])} Seeds × {len(manifest['scenarios'])} Szenarien), "
        f"gemeinsame Zufallszahlen über alle Szenarien",
        f"- Code: `{manifest['git_commit'][:12]}`" + (" (mit uncommitteten Änderungen)" if manifest["git_dirty"] else ""),
        f"- Laufzeit: {manifest['wall_seconds']} s Wandzeit auf {manifest['workers']} Prozessen",
        f"- Buchführungsinvarianten: {manifest['invariant_checks']}",
        f"- Replay-Prüfung (Lauf {manifest['replay_check']['job']} erneut gerechnet): "
        f"{'bitgleich' if manifest['replay_check']['identical'] else 'ABWEICHUNG'}",
        f"- Programmbudget je Instrument: Median {_fmt(budget.median())} Mio. € "
        f"(Spanne {_fmt(budget.min())}–{_fmt(budget.max())}) über 24 Monate",
        f"- Parameterstatus laut Profilen: " + ", ".join(f"{k}: {v}" for k, v in sorted(status.items())),
        "",
        "## Verläufe", "",
    ]
    md += [f"![{f}]({f})" for f in figs] + [""]
    md += ["## Niveaus (Median über Seeds)", "", _table(wide.reset_index()), ""]
    md += ["## Gepaarte Differenzen zu " + reference, "",
           "Differenz Szenario − Referenz je Seed (gleiche Zufallszahlen). `share_positive` = Anteil der Seeds "
           "mit positiver Differenz. Alle Zahlen: `paired_differences.csv`.", ""]
    for sc in [s for s in main if s != reference]:
        d = diffs[diffs.scenario == sc].drop(columns=["scenario", "n"])
        md += [f"### {LABELS.get(sc, sc)}", "", _table(d), ""]
    if checks:
        md += ["## Mechanismus-Erwartungen (vorab festgelegt)", "",
               "Anteil der Seeds, in denen die Erwartung zutrifft. Prüft die Umsetzung der Mechanismen, "
               "nicht die Wirklichkeit.", "", "| ID | Erwartung | Anteil Seeds |", "|---|---|---|"]
        md += [f"| {i} | {d} | {v:.2f} |" for i, d, v in checks] + [""]
    if stat is not None:
        md += ["## Quasistationarität der Basis (Kontrolllauf ohne Schock)", "",
               "Mittel Monate 48–59 gegenüber −12…−1.", "", _table(stat), ""]
    md += ["## Entscheidungsmodelle", "", "| Komponente | Modell | Art | Aufrufe | Einzelentscheidungen | Sekunden | ungültige Aktionen |",
           "|---|---|---|---|---|---|---|"]
    for name, d in manifest["decision_models"].items():
        md.append(f"| {name} | {d['model']} {d['version']} | {d['kind']} | {d['calls']} | {d['agent_decisions']} | "
                  f"{d['seconds']} | {d['invalid_actions']} |")
    for name, d in manifest["decision_models"].items():
        if d.get("params"):
            md.append(f"\n`{name}` Parameter: " + ", ".join(f"{k}={v}" for k, v in d["params"].items()))
        if d.get("table_fallbacks"):
            md.append(f"\n`{name}`: {d['table_fallbacks']} Entscheidungen ohne gültigen Tabelleneintrag (Änderung 0 verwendet)")
    md += ["", f"Laufzeit-Flags (Summe über alle Läufe): {manifest['run_flags']}", ""]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    return out / "report.md"
