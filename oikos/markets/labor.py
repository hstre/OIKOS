"""Labour market protocol: layoffs, then random matching of unemployed
workers to vacancies. Every household supplies one unit of labour."""

from __future__ import annotations

import numpy as np


def adjust_employment(employer: np.ndarray, employers: np.ndarray, target: np.ndarray,
                      max_layoff: np.ndarray, rng: np.random.Generator,
                      separation_rate: float = 0.0, search_rate: float = 1.0):
    """Bring each employer's workforce towards its target.

    employer:   household -> employer entity id, -1 if unemployed (modified in place)
    employers:  entity ids of all employers (order matches target / max_layoff)
    target:     desired number of workers
    max_layoff: maximum number of workers an employer may dismiss this period

    separation_rate: share of employed workers leaving their job each period
                     for reasons outside the model (turnover)
    search_rate:     probability that an unemployed worker reaches a vacancy
                     in this period (matching friction)

    Returns (fired, hired, unfilled_vacancies) per employer.
    """
    if separation_rate > 0:
        leave = (employer >= 0) & (rng.random(employer.size) < separation_rate)
        employer[leave] = -1
    n_emp = employers.size
    fired = np.zeros(n_emp, dtype=np.int64)
    hired = np.zeros(n_emp, dtype=np.int64)
    current = workforce(employer, employers)

    for j in range(n_emp):
        excess = current[j] - int(target[j])
        if excess > 0:
            n_fire = min(excess, int(max_layoff[j]))
            if n_fire > 0:
                staff = np.nonzero(employer == employers[j])[0]
                gone = rng.choice(staff, size=n_fire, replace=False)
                employer[gone] = -1
                fired[j] = n_fire

    vacancies = np.maximum(0, target.astype(np.int64) - workforce(employer, employers))
    unemployed = np.nonzero(employer < 0)[0]
    searching = unemployed[rng.random(unemployed.size) < search_rate]
    pool = rng.permutation(searching)
    pos = 0
    for j in rng.permutation(n_emp):
        take = int(min(vacancies[j], pool.size - pos))
        if take > 0:
            employer[pool[pos:pos + take]] = employers[j]
            hired[j] = take
            pos += take
    unfilled = vacancies - hired
    return fired, hired, unfilled


def workforce(employer: np.ndarray, employers: np.ndarray) -> np.ndarray:
    """Number of workers per employer."""
    lookup = {int(e): k for k, e in enumerate(employers)}
    counts = np.zeros(employers.size, dtype=np.int64)
    emp = employer[employer >= 0]
    if emp.size:
        uniq, c = np.unique(emp, return_counts=True)
        for u, cnt in zip(uniq, c):
            counts[lookup[int(u)]] = cnt
    return counts
