"""LLM-derived decision table for the household budget decision.

Household situations are discretised into a finite set of cells
(employment x income quintile x energy price relative to the habitual
price x energy bill share x savings). An LLM answers once per cell how a
typical household in that situation changes its energy use and its other
spending relative to its normal behaviour. The answers are stored as a
table file, so that

- the cost depends on the number of cells, not on households, months or seeds,
- simulations run offline, in parallel and reproduce bit for bit,
- the table can be read, reviewed and corrected by people (CSV export).

Within a cell, households keep their individual needs, propensities and
budgets: the table modulates the rule-based decision, it does not replace
heterogeneity. Discretisation is an approximation whose effect has to be
measured (finer bins = more cells).
"""

from __future__ import annotations

import csv
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from ..protocol import ActionSpace, Box, DecisionBatch, ModelMeta, ObservationBatch

PROMPT_VERSION = "household_table_v1"

EMPLOYMENT = ("employed", "unemployed")
QUINTILES = ("in the lowest fifth of the income distribution", "in the second-lowest fifth",
             "in the middle fifth", "in the second-highest fifth", "in the highest fifth")
PRICE_EDGES = (0.9, 1.1, 1.3, 1.6, 2.0)
PRICE_TEXT = ("more than 10 % lower than", "roughly the same as", "10–30 % higher than",
              "30–60 % higher than", "60–100 % higher than", "more than twice")
BURDEN_EDGES = (0.05, 0.10, 0.15, 0.25)
BURDEN_TEXT = ("below 5 %", "5–10 %", "10–15 %", "15–25 %", "above 25 %")
SAVINGS_EDGES = (1.0, 3.0, 6.0, 12.0)
SAVINGS_TEXT = ("less than one month", "one to three months", "three to six months",
                "six to twelve months", "more than a year")
SHAPE = (len(EMPLOYMENT), len(QUINTILES), len(PRICE_TEXT), len(BURDEN_TEXT), len(SAVINGS_TEXT))
N_CELLS = int(np.prod(SHAPE))

ENERGY_BOUNDS = (-0.5, 0.1)
SPENDING_BOUNDS = (-0.5, 0.3)

SYSTEM_PROMPT = (
    "You describe the economic behaviour of private households for an agent-based research "
    "simulation. Describe how a typical household in the given situation actually behaves this "
    "month, including habits, limited information, liquidity constraints and precautionary "
    "motives. Do not recommend what would be optimal. If behaviour in such a situation is "
    "uncertain, give your best central estimate. Answer only with the requested JSON."
)

USER_TEMPLATE = (
    "Context: a stylised high-income European economy, prices in euro.\n"
    "Household situation this month:\n"
    "- The main earner is {employment}.\n"
    "- The household's net income is {quintile}.\n"
    "- The energy price it pays now is {price} what it is used to paying.\n"
    "- At its usual energy use, the energy bill would be {burden} of its monthly net income.\n"
    "- Its savings correspond to {savings} of net income.\n\n"
    "Compared with its normal behaviour at usual prices, by how much does this household change\n"
    "(a) its energy use (heating, electricity) and\n"
    "(b) its spending on all other goods and services this month?\n"
    "Give relative changes as decimals, e.g. -0.10 for a reduction by 10 %. "
    f"energy_use_change must lie between {ENERGY_BOUNDS[0]} and {ENERGY_BOUNDS[1]}, "
    f"other_spending_change between {SPENDING_BOUNDS[0]} and {SPENDING_BOUNDS[1]}."
)

JSON_SCHEMA = {
    "name": "household_adjustment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "energy_use_change": {"type": "number"},
            "other_spending_change": {"type": "number"},
            "main_reason": {"type": "string"},
        },
        "required": ["energy_use_change", "other_spending_change", "main_reason"],
        "additionalProperties": False,
    },
}


def prompt_hash() -> str:
    blob = json.dumps([PROMPT_VERSION, SYSTEM_PROMPT, USER_TEMPLATE, JSON_SCHEMA], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- cells
def cell_coords(cell: int) -> tuple[int, ...]:
    return tuple(int(x) for x in np.unravel_index(cell, SHAPE))


def describe(cell: int) -> dict[str, str]:
    e, q, p, b, s = cell_coords(cell)
    return {"employment": EMPLOYMENT[e], "quintile": QUINTILES[q], "price": PRICE_TEXT[p],
            "burden": BURDEN_TEXT[b], "savings": SAVINGS_TEXT[s]}


def messages_for(cell: int) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(**describe(cell))}]


def cells_of(obs: ObservationBatch) -> np.ndarray:
    """Map observations to cell indices."""
    employed = obs["employed"].astype(bool)
    e = np.where(employed, 0, 1)
    q = np.clip(obs["income_quintile"].astype(int), 0, 4)
    p = np.digitize(obs["energy_price"] / obs["reference_price"], PRICE_EDGES)
    income = np.maximum(obs["net_income"], 1.0)
    b = np.digitize(obs["need_kwh"] * obs["energy_price"] / income, BURDEN_EDGES)
    s = np.digitize(np.maximum(obs["wealth_before_income"], 0.0) / income, SAVINGS_EDGES)
    return np.ravel_multi_index((e, q, p, b, s), SHAPE)


# --------------------------------------------------------------- building
def parse_answer(content: str) -> tuple[dict, bool]:
    try:
        d = json.loads(content)
        en = float(d["energy_use_change"])
        sp = float(d["other_spending_change"])
    except (ValueError, KeyError, TypeError):
        return {"energy_use_change": 0.0, "other_spending_change": 0.0, "raw": content[:200]}, False
    ok = (ENERGY_BOUNDS[0] <= en <= ENERGY_BOUNDS[1]) and (SPENDING_BOUNDS[0] <= sp <= SPENDING_BOUNDS[1])
    return {"energy_use_change": float(np.clip(en, *ENERGY_BOUNDS)),
            "other_spending_change": float(np.clip(sp, *SPENDING_BOUNDS)),
            "main_reason": str(d.get("main_reason", ""))[:200]}, ok


def build_table(client, model: str, out_path: str | Path, *, temperature: float = 0.0, seed: int = 0,
                max_tokens: int = 200, concurrency: int = 8, max_calls: int = N_CELLS,
                max_cost_usd: float = 2.0, cells: list[int] | None = None, log=print) -> Path:
    """Query the LLM for every cell not yet in the table file (resumable)."""
    out_path = Path(out_path)
    table = json.loads(out_path.read_text()) if out_path.exists() else None
    if table and (table["meta"]["model_requested"] != model or table["meta"]["prompt_hash"] != prompt_hash()):
        raise ValueError(f"{out_path} was built with another model or prompt; use a new file")
    if table is None:
        table = {"meta": {"model_requested": model, "prompt_version": PROMPT_VERSION, "prompt_hash": prompt_hash(),
                          "system_prompt": SYSTEM_PROMPT, "user_template": USER_TEMPLATE, "json_schema": JSON_SCHEMA,
                          "temperature": temperature, "seed": seed, "max_tokens": max_tokens,
                          "shape": SHAPE, "n_cells": N_CELLS, "models_answered": [], "calls": 0,
                          "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "invalid": 0,
                          "created_unix": int(time.time())},
                 "cells": {}}
    meta = table["meta"]
    todo = [c for c in (cells if cells is not None else range(N_CELLS)) if str(c) not in table["cells"]]
    todo = todo[: max(0, max_calls - meta["calls"])]
    log(f"{len(table['cells'])} cells present, {len(todo)} to query with {model}")

    lock = threading.Lock()
    spent = {"usd": meta["cost_usd"]}

    def ask(c):
        # The cost limit is checked before every request, so requests already
        # queued in the pool are skipped once the limit is reached.
        with lock:
            if spent["usd"] > max_cost_usd:
                return c, None
        comp = client.complete(model, messages_for(c), temperature=temperature, seed=seed,
                               max_tokens=max_tokens, json_schema=JSON_SCHEMA)
        with lock:
            spent["usd"] += comp.cost_usd
        return c, comp

    stopped = None
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(ask, c) for c in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                c, comp = fut.result()
            except Exception as e:  # noqa: BLE001 - keep what was obtained so far
                stopped = stopped or f"error: {e}"
                continue
            if comp is None:
                stopped = f"cost limit {max_cost_usd} USD reached"
                continue
            answer, ok = parse_answer(comp.content)
            answer["valid"] = ok
            answer["model"] = comp.model
            table["cells"][str(c)] = answer
            meta["calls"] += 1
            meta["prompt_tokens"] += comp.prompt_tokens
            meta["completion_tokens"] += comp.completion_tokens
            meta["cost_usd"] += comp.cost_usd
            meta["invalid"] += int(not ok)
            if comp.model not in meta["models_answered"]:
                meta["models_answered"].append(comp.model)
            if i % 100 == 0:
                log(f"  {i}/{len(todo)} cells, {meta['cost_usd']:.4f} USD")
                _save(table, out_path)
    meta["complete"] = len(table["cells"]) == N_CELLS
    meta["stopped"] = stopped
    _save(table, out_path)
    export_csv(table, out_path.with_suffix(".csv"))
    log(f"done: {len(table['cells'])}/{N_CELLS} cells, {meta['invalid']} invalid, "
        f"{meta['cost_usd']:.4f} USD" + (f", stopped: {stopped}" if stopped else ""))
    return out_path


def _save(table: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(table, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def export_csv(table: dict, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cell", "employment", "income", "energy_price_vs_usual", "energy_bill_share", "savings",
                    "energy_use_change", "other_spending_change", "valid", "main_reason"])
        for key in sorted(table["cells"], key=int):
            a = table["cells"][key]
            d = describe(int(key))
            w.writerow([key, d["employment"], d["quintile"], d["price"], d["burden"], d["savings"],
                        a["energy_use_change"], a["other_spending_change"], a["valid"], a.get("main_reason", "")])


# ------------------------------------------------------------ the model
class TableHouseholdModel:
    """Household budget decision modulated by an LLM-derived decision table.

    energy wanted = need * (1 + energy_use_change[cell])
    goods budget  = rule budget (after actual energy cost) * (1 + other_spending_change[cell])
    Cells missing from the table, or with invalid answers, use change 0 (counted)."""

    def __init__(self, table_path: str | Path):
        path = Path(table_path)
        raw = path.read_bytes()
        table = json.loads(raw)
        meta = table["meta"]
        self.energy = np.zeros(N_CELLS)
        self.spending = np.zeros(N_CELLS)
        self.known = np.zeros(N_CELLS, dtype=bool)
        for key, a in table["cells"].items():
            if a.get("valid", False):
                c = int(key)
                self.energy[c] = a["energy_use_change"]
                self.spending[c] = a["other_spending_change"]
                self.known[c] = True
        self.lookups = 0
        self.fallbacks = 0
        self.meta = ModelMeta(
            name="household_llm_table", version=meta["prompt_version"], kind="llm", deterministic=True,
            probability_semantics="none",
            validation="not validated against behavioural data",
            params={"table_sha256_16": hashlib.sha256(raw).hexdigest()[:16],
                    "model_requested": meta["model_requested"],
                    "models_answered": ",".join(meta["models_answered"]),
                    "cells_valid": int(self.known.sum()), "cells_total": N_CELLS},
        )

    @staticmethod
    def action_space(obs: ObservationBatch) -> ActionSpace:
        return {
            "energy_wanted": Box(0.0, obs["need_kwh"]),
            "energy_kwh": Box(0.0, obs["need_kwh"]),
            "goods_budget": Box(0.0, obs["deposits"].astype(float)),
        }

    def decide(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        cells = cells_of(obs)
        self.lookups += cells.size
        self.fallbacks += int((~self.known[cells]).sum())
        need, price = obs["need_kwh"], obs["energy_price"]
        wanted = np.clip(need * (1 + self.energy[cells]), 0.0, need)
        deposits = obs["deposits"].astype(float)
        energy = np.minimum(wanted, np.floor(deposits) / price)
        cost = energy * price
        remaining = np.maximum(0.0, deposits - np.ceil(cost))
        budget = (obs["c_income"] * np.maximum(0.0, obs["net_income"] - cost)
                  + obs["c_wealth"] * np.maximum(0.0, obs["wealth_before_income"]))
        budget = budget * (1 + self.spending[cells])
        return {"energy_wanted": wanted, "energy_kwh": energy, "goods_budget": np.minimum(budget, remaining)}
