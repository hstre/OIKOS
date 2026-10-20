"""python -m oikos.empirics sce-validation [--mode live|replay] [--replay-log LOG] [--out DIR]

Fetches the SCE files (SHA-256 pinned), builds the registered sample and split,
runs the registered Jev requests and evaluates all models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from ..behavior.jev.client import MissingKeyError
from . import jev_sce, sce


def main() -> None:
    ap = argparse.ArgumentParser(prog="oikos.empirics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("sce-validation")
    v.add_argument("--spec", default="configs/experiments/sce_validation.yaml")
    v.add_argument("--mode", choices=["live", "replay"], default="live")
    v.add_argument("--replay-log", default=None)
    v.add_argument("--out", default="results/sce_validation")
    args = ap.parse_args()
    spec = yaml.safe_load(Path(args.spec).read_text())
    sce.fetch(spec["data"]["raw_dir"])
    df = sce.assign(sce.build(spec["data"]["raw_dir"]), spec)
    sce.check_no_leakage(df)
    try:
        res = jev_sce.run(spec, df, args.out, mode=args.mode, replay_log=args.replay_log)
    except MissingKeyError as e:
        sys.exit(f"Jev: {e}. Set it in the execution environment, never in files or Git.")
    print(json.dumps({k: res[k] for k in ("requests", "errors_by_kind", "cost_usd_logged", "primary")}, indent=2))
    sys.exit(1 if res["errors_by_kind"] else 0)


if __name__ == "__main__":
    main()
