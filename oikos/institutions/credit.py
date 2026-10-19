"""Credit regulation: a minimum capital ratio caps total bank lending to
the private sector. Government borrowing is not capped in v0.1 (explicit
simplification: the state can always refinance at the bank)."""

from __future__ import annotations

import numpy as np


def apply_capital_requirement(granted: np.ndarray, bank_equity: int, private_loans: int,
                              min_capital_ratio: float) -> np.ndarray:
    """Scale individual grants down proportionally so that
    private loans after lending <= bank equity / min_capital_ratio."""
    if min_capital_ratio <= 0:
        return granted
    room = max(0.0, bank_equity / min_capital_ratio - private_loans)
    total = float(granted.sum())
    if total <= room or total == 0:
        return granted
    return np.floor(granted * (room / total))
