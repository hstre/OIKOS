"""Tax, benefit and spending rules of the government."""

from __future__ import annotations

from collections import deque


class FiscalRules:
    """Flat income and profit taxes, unemployment benefit as a share of the
    average wage, and a smoothed balanced-budget rule for regular public
    purchases: purchases = mean(taxes) - mean(benefits) - mean(interest)
    over the last `smoothing_months`. Spending of temporary policy programmes
    is financed by borrowing and is not part of this rule."""

    def __init__(self, cfg: dict):
        self.income_tax_rate = float(cfg["income_tax_rate"])
        self.profit_tax_rate = float(cfg["profit_tax_rate"])
        self.benefit_replacement = float(cfg["unemployment_benefit_replacement"])
        self.smoothing = int(cfg["spending_smoothing_months"])
        self._taxes: deque[int] = deque(maxlen=self.smoothing)
        self._benefits: deque[int] = deque(maxlen=self.smoothing)
        self._interest: deque[int] = deque(maxlen=self.smoothing)

    def income_tax(self, gross):
        return (gross * self.income_tax_rate).astype("int64")

    def profit_tax(self, profit):
        return (profit.clip(min=0) * self.profit_tax_rate).astype("int64")

    def benefit(self, average_wage: float) -> int:
        return int(self.benefit_replacement * average_wage)

    def record(self, taxes: int, benefits: int, interest: int) -> None:
        self._taxes.append(taxes)
        self._benefits.append(benefits)
        self._interest.append(interest)

    def purchases(self, fallback: int) -> int:
        if not self._taxes:
            return fallback
        n = len(self._taxes)
        value = (sum(self._taxes) - sum(self._benefits) - sum(self._interest)) / n
        return max(0, int(value))
