"""Command line:
    python -m oikos run <experiment.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos sensitivity <sensitivity.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos report <experiment-dir>
    python -m oikos llm-table --model <openrouter-model-id> --out <table.json> [--max-cost-usd X]
    python -m oikos compare <experiment-dir-A> <experiment-dir-B>
    python -m oikos jev-ping [--spec configs/experiments/jev_observe.yaml]
    python -m oikos jev-observe [--spec ...] [--mode live|replay] [--replay-log LOG] [--out DIR]
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
    jp = sub.add_parser("jev-ping", help="one real Jev request with a fixed example household")
    jp.add_argument("--spec", default="configs/experiments/jev_observe.yaml")
    jp.add_argument("--out", default="results/jev_observe/ping.json")
    jo = sub.add_parser("jev-observe", help="observation run: rules control, Jev is logged (max 50 decisions)")
    jo.add_argument("--spec", default="configs/experiments/jev_observe.yaml")
    jo.add_argument("--mode", choices=["live", "replay"], default=None)
    jo.add_argument("--replay-log", default=None)
    jo.add_argument("--out", default=None)
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
    elif args.cmd in ("jev-ping", "jev-observe"):
        import json as _json
        import sys

        from .behavior.jev.client import MissingKeyError
        from .experiments.jev_observe import ping, run_observation

        try:
            if args.cmd == "jev-ping":
                r = ping(args.spec, args.out)
                show = {k: r.get(k) for k in ("status", "http_status", "error_kind", "error", "model_served",
                                              "provider", "input_tokens", "cost_usd", "latency_s", "parsed")}
            else:
                r = run_observation(args.spec, args.out, args.mode, args.replay_log)
                show = {k: r[k] for k in ("mode", "requests", "ok", "errors", "errors_by_kind", "models_served",
                                          "cost_usd_total", "latency_s_median", "same_option_as_rule_share",
                                          "economy_unchanged_by_observation")}
        except MissingKeyError as e:
            sys.exit(f"Jev: {e}. Set it in the execution environment, never in files or Git.")
        print(_json.dumps(show, indent=2, ensure_ascii=False))
        failed = show.get("status") == "error" or show.get("errors")
        sys.exit(1 if failed else 0)
    else:
        print(build_report(args.directory))


if __name__ == "__main__":
    main()
