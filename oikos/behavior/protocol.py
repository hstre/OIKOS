"""Interface between the simulation and any decision model.

A decision model receives a batch of observations for all agents that
decide in this period and a closed, typed action space. It returns one
action per agent. Rules, statistical models, small networks, System-1
models (structured decisions, no text) and LLMs all implement the same
interface, so they can be swapped without touching accounting or
institutions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Mapping, Protocol

import numpy as np

ModelKind = Literal["rule", "statistical", "nn", "system1", "llm"]
# What a probability-like output of the model means. Only
# "calibrated_choice_prob" may be read as the probability that a person
# would choose an action; "score" is a model-internal preference.
ProbabilitySemantics = Literal["none", "score", "calibrated_choice_prob"]

ObservationBatch = Mapping[str, np.ndarray]
DecisionBatch = dict[str, np.ndarray]


@dataclass(frozen=True)
class ModelMeta:
    name: str
    version: str
    kind: ModelKind
    deterministic: bool
    probability_semantics: ProbabilitySemantics = "none"
    validation: str = "not validated against behavioural data"
    params: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Box:
    """Continuous action in [low, high] (per agent, broadcastable)."""

    low: np.ndarray | float
    high: np.ndarray | float

    def valid(self, a: np.ndarray) -> np.ndarray:
        return np.isfinite(a) & (a >= self.low) & (a <= self.high)

    def fallback(self, a: np.ndarray) -> np.ndarray:
        return np.clip(np.nan_to_num(a, nan=np.asarray(self.low, dtype=float)), self.low, self.high)


ActionSpace = Mapping[str, Box]


class DecisionModel(Protocol):
    meta: ModelMeta

    def decide(
        self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator
    ) -> DecisionBatch: ...


class DecisionShapeError(ValueError):
    """A decision model returned missing actions or arrays of the wrong length."""


@dataclass
class CallStats:
    calls: int = 0
    agents: int = 0
    seconds: float = 0.0
    invalid_actions: int = 0


class Decider:
    """Wraps a decision model: validates actions against the action space,
    replaces invalid ones by the documented fallback (clipping) and counts
    calls, agents, time and invalid actions."""

    def __init__(self, model: DecisionModel):
        self.model = model
        self.stats = CallStats()

    def __call__(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        n = len(next(iter(obs.values()))) if obs else 0
        t0 = time.perf_counter()
        out = self.model.decide(obs, space, rng)
        self.stats.seconds += time.perf_counter() - t0
        self.stats.calls += 1
        self.stats.agents += n
        checked: DecisionBatch = {}
        missing = [name for name in space if name not in out]
        if missing:
            raise DecisionShapeError(f"{self.model.meta.name}: actions {missing} missing")
        for name, box in space.items():
            a = np.asarray(out[name], dtype=float)
            if a.shape != (n,):
                # never broadcast: a wrong length means the model answered for other agents
                raise DecisionShapeError(f"{self.model.meta.name}: action {name!r} has shape {a.shape}, expected ({n},)")
            ok = box.valid(a)
            bad = int((~ok).sum())
            if bad:
                self.stats.invalid_actions += bad
                a = np.where(ok, a, box.fallback(a))
            checked[name] = a
        return checked
