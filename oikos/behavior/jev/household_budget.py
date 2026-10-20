"""Jev decision 1: choice between given consumption budgets.

Scope (deliberately narrow):
- One decision: how much a household spends this month on goods and
  services other than energy, chosen from a fixed set of budgets.
- The energy decision and everything else stays with the v0.1 rules.
- The state contains only what the household itself knows: its own
  employment status, this month's net income, its savings, the energy
  price it pays now and the price it is used to, this month's energy bill
  and the money left after it. No model parameters (propensities), no
  income rank, no information about other households or the economy.
- Budgets are defined independently of the rule, as shares of the income
  left after the energy bill, so the rule's answer is not one of the
  options by construction.

Jev's probabilities are recorded as model-internal scores
(probability_semantics = "score"). They are not empirical probabilities
of human choice.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from .client import CallRecord, DecisionClient, InvalidActionError, ResponseFormatError

QUESTION_ID = "goods_budget"
DECISION_VERSION = "household_goods_budget_v1"
PROBABILITY_SEMANTICS = "score"
PROB_SUM_TOLERANCE = 0.05

INSTRUCTIONS = (
    "Which of the listed budgets for goods and services other than energy is this household "
    "most likely to set for this month? Consider only what the household knows about its own "
    "situation as given in the state."
)
CONTEXT = ("A private household in a stylised European economy. All amounts are euro per month. "
           "The energy bill for this month is already fixed.")


def _eur(cents: float) -> int:
    return int(round(cents / 100.0))


def budget_options(net_income: float, energy_cost: float, deposits: float,
                   fractions: list[float]) -> dict[str, int]:
    """Options in cents: shares of income after the energy bill, rounded to
    10 €, never above the money available. Keys b1..bn in ascending order."""
    base = max(0.0, net_income - energy_cost)
    available = max(0.0, deposits - energy_cost)
    out = {}
    for i, f in enumerate(sorted(fractions), 1):
        amount = min(f * base, available)
        out[f"b{i}"] = int(round(amount / 1000.0)) * 1000  # 10 € steps, in cents
    return out


def build_request(model: str, *, employed: bool, net_income: float, savings: float, deposits: float,
                  price_now: float, price_usual: float, energy_cost: float,
                  fractions: list[float]) -> tuple[dict, dict[str, int]]:
    """Return the Decisions request body and the option amounts (cents)."""
    options = budget_options(net_income, energy_cost, deposits, fractions)
    base = max(0.0, net_income - energy_cost)
    state = {
        "context": CONTEXT,
        "household": {
            "employment": "employed" if employed else "unemployed, receives unemployment benefit",
            "net_income_this_month_eur": _eur(net_income),
            "savings_before_this_months_income_eur": _eur(savings),
            "energy_price_now_ct_per_kwh": round(price_now, 1),
            "energy_price_usually_paid_ct_per_kwh": round(price_usual, 1),
            "energy_bill_this_month_eur": _eur(energy_cost),
            "money_available_after_energy_bill_eur": _eur(max(0.0, deposits - energy_cost)),
        },
    }
    criteria = {}
    for (key, amount), f in zip(options.items(), sorted(fractions)):
        share = amount / base if base > 0 else 0.0
        criteria[key] = f"Spend about {_eur(amount)} € (about {share:.0%} of the income left after the energy bill)."
    body = {"model": model, "state": state,
            "questions": {QUESTION_ID: {"type": "choice", "instructions": INSTRUCTIONS, "criteria": criteria}}}
    return body, options


def parse_choice(response: dict | None, option_keys: list[str],
                 question_id: str = QUESTION_ID) -> tuple[str, dict[str, float], float | None]:
    """Validate a Decisions response for the budget question.

    Raises ResponseFormatError for missing or malformed fields and wrong
    numbers of probabilities, InvalidActionError for a choice outside the
    option set. Nothing is repaired."""
    if not isinstance(response, dict):
        raise ResponseFormatError("response missing")
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise ResponseFormatError("field 'answers' missing")
    if set(answers) != {question_id}:
        raise ResponseFormatError(f"expected exactly one answer '{question_id}', got {sorted(answers)}")
    a = answers[question_id]
    if not isinstance(a, dict) or a.get("type") != "choice":
        raise ResponseFormatError("answer is not of type 'choice'")
    if "choice" not in a:
        raise ResponseFormatError("field 'choice' missing")
    choice = a["choice"]
    if choice not in option_keys:
        raise InvalidActionError(f"choice {choice!r} is not one of {option_keys}")
    probs = a.get("probabilities")
    if not isinstance(probs, dict):
        raise ResponseFormatError("field 'probabilities' missing")
    if len(probs) != len(option_keys) or set(probs) != set(option_keys):
        raise ResponseFormatError(f"probabilities for {sorted(probs)} do not match the {len(option_keys)} options")
    try:
        p = {k: float(v) for k, v in probs.items()}
    except (TypeError, ValueError) as e:
        raise ResponseFormatError("non-numeric probability") from e
    if any((not math.isfinite(v)) or v < 0 or v > 1 for v in p.values()):
        raise ResponseFormatError("probability outside [0, 1]")
    if abs(sum(p.values()) - 1.0) > PROB_SUM_TOLERANCE:
        raise ResponseFormatError(f"probabilities sum to {sum(p.values()):.3f}")
    conf = a.get("confidence")
    return choice, p, (float(conf) if isinstance(conf, (int, float)) else None)


class JevBudgetObserver:
    """Observation mode: the rule keeps controlling the economy. For a small
    sample of households in selected months, the same decision is put to
    Jev and the answer is logged next to the rule's decision.

    Hard limit: at most `max_decisions` requests per run (default 50).
    Errors are logged with their type and counted; they are never replaced
    by the rule's decision."""

    HARD_LIMIT = 50

    def __init__(self, client: DecisionClient, cfg: dict, log_path: str | Path, log=print):
        self.client = client
        self.model = cfg["model"]
        self.months = [int(m) for m in cfg["months"]]
        self.per_month = int(cfg["households_per_month"])
        self.fractions = [float(f) for f in cfg["budget_fractions"]]
        self.max_decisions = int(cfg["max_decisions"])
        if self.max_decisions > self.HARD_LIMIT:
            raise ValueError(f"max_decisions {self.max_decisions} exceeds the hard limit {self.HARD_LIMIT}")
        if len(self.months) * self.per_month > self.max_decisions:
            raise ValueError("months x households_per_month exceeds max_decisions")
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("", encoding="utf-8")
        self.n_requests = 0
        self.rows: list[dict] = []
        self._log = log

    def wants(self, t: int) -> bool:
        return t in self.months

    def _write(self, entry: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def sample(n: int, per_month: int, rng: np.random.Generator) -> np.ndarray:
        return np.sort(rng.choice(n, size=min(per_month, n), replace=False))

    def observe(self, t: int, obs: dict, decision: dict, rng: np.random.Generator) -> None:
        sample = self.sample(len(obs["deposits"]), self.per_month, rng)
        for i in sample:
            if self.n_requests >= self.max_decisions:
                raise RuntimeError("decision limit reached")  # cannot happen given the checks above
            self.n_requests += 1
            price = float(obs["energy_price"][i])
            energy_cost = float(decision["energy_kwh"][i]) * price
            body, options = build_request(
                self.model, employed=bool(obs["employed"][i]), net_income=float(obs["net_income"][i]),
                savings=float(obs["wealth_before_income"][i]), deposits=float(obs["deposits"][i]),
                price_now=price, price_usual=float(obs["reference_price"][i]), energy_cost=energy_cost,
                fractions=self.fractions)
            rec: CallRecord = self.client.decide(body)
            row = {"type": "call", "t": t, "household": int(i), "decision": DECISION_VERSION,
                   "probability_semantics": PROBABILITY_SEMANTICS, "options_cents": options,
                   "rule_budget_cents": float(decision["goods_budget"][i]), **rec.to_dict()}
            row.update(self._compare(rec, options, row["rule_budget_cents"]))
            self._write(row)
            self.rows.append(row)
            if row["status"] != "ok":
                self._log(f"  t={t} household {i}: {row['error_kind']}: {row['error']}")

    @staticmethod
    def _compare(rec: CallRecord, options: dict[str, int], rule_budget: float) -> dict:
        keys = list(options)
        amounts = np.array([options[k] for k in keys], dtype=float)
        rule_option = keys[int(np.argmin(np.abs(amounts - rule_budget)))]
        out = {"rule_nearest_option": rule_option}
        if rec.status != "ok":
            return out
        try:
            choice, probs, conf = parse_choice(rec.response, keys)
        except (ResponseFormatError, InvalidActionError) as e:
            out.update(status="error", error_kind=e.kind, error=str(e)[:300])
            return out
        jev_budget = options[choice]
        out.update(
            jev_choice=choice, jev_budget_cents=jev_budget, jev_scores=probs, jev_confidence=conf,
            same_option_as_rule=choice == rule_option,
            option_steps_vs_rule=keys.index(choice) - keys.index(rule_option),
            budget_diff_vs_rule_rel=(jev_budget - rule_budget) / rule_budget if rule_budget > 0 else None,
            score_of_rule_option=probs[rule_option],
        )
        return out


def write_summary(rows: list[dict], path: str | Path, meta: dict) -> dict:
    ok = [r for r in rows if r["status"] == "ok"]
    err = [r for r in rows if r["status"] != "ok"]
    kinds: dict[str, int] = {}
    for r in err:
        kinds[r["error_kind"]] = kinds.get(r["error_kind"], 0) + 1
    costs = [r["cost_usd"] for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    lat = [r["latency_s"] for r in rows if isinstance(r.get("latency_s"), (int, float))]
    steps = [r["option_steps_vs_rule"] for r in ok]
    rel = [r["budget_diff_vs_rule_rel"] for r in ok if r.get("budget_diff_vs_rule_rel") is not None]
    by_month: dict[int, dict] = {}
    for r in ok:
        m = by_month.setdefault(r["t"], {"n": 0, "same": 0, "steps": []})
        m["n"] += 1
        m["same"] += int(r["same_option_as_rule"])
        m["steps"].append(r["option_steps_vs_rule"])
    s = {
        **meta,
        "requests": len(rows),
        "ok": len(ok),
        "errors": len(err),
        "errors_by_kind": kinds,
        "models_served": sorted({r["model_served"] for r in rows if r.get("model_served")}),
        "replayed": all(r.get("replayed") for r in rows) if rows else False,
        "cost_usd_total": round(sum(costs), 8) if costs else 0.0,
        "cost_usd_per_decision": round(sum(costs) / len(costs), 10) if costs else None,
        "latency_s_median": float(np.median(lat)) if lat else None,
        "latency_s_max": float(np.max(lat)) if lat else None,
        "same_option_as_rule_share": (sum(r["same_option_as_rule"] for r in ok) / len(ok)) if ok else None,
        "option_steps_vs_rule": {str(k): steps.count(k) for k in sorted(set(steps))},
        "budget_diff_vs_rule_rel_median": float(np.median(rel)) if rel else None,
        "by_month": {str(t): {"n": m["n"], "same_option_as_rule": m["same"],
                              "mean_option_steps": float(np.mean(m["steps"]))} for t, m in sorted(by_month.items())},
        "created_unix": int(time.time()),
    }
    Path(path).write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    return s
