"""Command line:
    python -m oikos run <experiment.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos sensitivity <sensitivity.yaml> [--seeds N] [--out DIR] [--workers K]
    python -m oikos report <experiment-dir>
"""

from __future__ import annotations

import argparse
from pathlib import Path

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
    rep = sub.add_parser("report", help="rebuild the report of an existing experiment directory")
    rep.add_argument("directory")
    sens = sub.add_parser("sensitivity", help="one-at-a-time sensitivity analysis")
    sens.add_argument("spec")
    sens.add_argument("--seeds", type=int, default=None)
    sens.add_argument("--out", default=None)
    sens.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    if args.cmd == "run":
        out = args.out or str(Path("results") / Path(args.experiment).stem)
        d = run_experiment(args.experiment, out, args.seeds, args.workers)
        print(build_report(d))
    elif args.cmd == "sensitivity":
        out = args.out or str(Path("results") / Path(args.spec).stem)
        print(run_sensitivity(args.spec, out, args.seeds, args.workers) / "sensitivity.md")
    else:
        print(build_report(args.directory))


if __name__ == "__main__":
    main()
