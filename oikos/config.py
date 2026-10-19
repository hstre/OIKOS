"""Configuration loading. A scenario is a nested override of the baseline."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            if k not in out:
                raise KeyError(f"override sets unknown key {k!r}")
            out[k] = copy.deepcopy(v)
    return out


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_experiment(path: str | Path) -> dict:
    path = Path(path)
    exp = load_yaml(path)
    exp["base_config"] = load_yaml((path.parent / exp["base"]).resolve())
    return exp


def config_hash(cfg: dict) -> str:
    blob = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
