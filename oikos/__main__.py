"""Command line:
    python -m oikos run <experiment.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos sensitivity <sensitivity.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos report <experiment-dir>
    python -m oikos llm-table --model <openrouter-model-id> --out <table.json> [--max-cost-usd X]
    python -m oikos compare <experiment-dir-A> <experiment-dir-B>
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from .experiments.report import build_report
from .experiments.runner import run_experiment
from .experiments.sensitivity import run_sensitivity


def main() -> None:
    ap = argparse.ArgumentParser(prog="oikos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run an experiment and write the report")
    run.add_argument("experiment")
    run.add_argument("--seeds", type=int, default=None, help="number of seeds (default: from experiment file)")
    run.add_argument("--out", default=None)
    run.add_argument("--workers", type=int, default=None)
    run.add_argument("--override", default=None,
                     help="YAML mapping merged into every scenario, e.g. '{behavior: {household: {table: x.json}}}'")
    rep = sub.add_parser("report", help="rebuild the report of an existing experiment directory")
    rep.add_argument("directory")
    sens = sub.add_parser("sensitivity", help="one-at-a-time sensitivity analysis")
    sens.add_argument("spec")
    sens.add_argument("--seeds", type=int, default=None)
    sens.add_argument("--out", default=None)
    sens.add_argument("--workers", type=int, default=None)
    tab = sub.add_parser("llm-table", help="build an LLM decision table for households (needs OPENROUTER_API_KEY)")
    tab.add_argument("--model", required=True)
    tab.add_argument("--out", required=True)
    tab.add_argument("--max-cost-usd", type=float, default=2.0)
    tab.add_argument("--max-calls", type=int, default=None)
    tab.add_argument("--concurrency", type=int, default=8)
    cmp_ = sub.add_parser("compare", help="compare scenario effects of two experiment directories")
    cmp_.add_argument("dir_a")
    cmp_.add_argument("dir_b")
    args = ap.parse_args()

    if args.cmd == "run":
        out = args.out or str(Path("results") / Path(args.experiment).stem)
        override = yaml.safe_load(args.override) if args.override else None
        d = run_experiment(args.experiment, out, args.seeds, args.workers, override)
        print(build_report(d))
    elif args.cmd == "sensitivity":
        out = args.out or str(Path("results") / Path(args.spec).stem)
        print(run_sensitivity(args.spec, out, args.seeds, args.workers) / "sensitivity.md")
    elif args.cmd == "llm-table":
        from .behavior.llm.household_table import N_CELLS, build_table
        from .behavior.llm.openrouter import OpenRouterClient

        build_table(OpenRouterClient(), args.model, args.out, max_cost_usd=args.max_cost_usd,
                    max_calls=args.max_calls or N_CELLS, concurrency=args.concurrency)
    elif args.cmd == "compare":
        from .experiments.compare import compare

        print(compare(args.dir_a, args.dir_b))
    else:
        print(build_report(args.directory))


if __name__ == "__main__":
    main()
