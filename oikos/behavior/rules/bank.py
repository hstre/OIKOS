"""Rule-based credit decision of the bank for individual requests.

The bank grants a request as long as the borrower's debt stays below a
multiple of its expected annual revenue. The aggregate capital
requirement is an institution, applied afterwards (see
oikos.institutions.credit).
"""

from __future__ import annotations

import numpy as np

from ..protocol import ActionSpace, Box, DecisionBatch, ModelMeta, ObservationBatch


class LeverageCreditRule:
    def __init__(self, max_debt_to_annual_revenue: float):
        self.max_ratio = float(max_debt_to_annual_revenue)
        self.meta = ModelMeta(
            name="leverage_credit_rule", version="0.1.0", kind="rule", deterministic=True,
            params={"max_debt_to_annual_revenue": self.max_ratio},
        )

    @staticmethod
    def action_space(obs: ObservationBatch) -> ActionSpace:
        return {"granted": Box(0.0, obs["requested"].astype(float))}

    def decide(self, obs: ObservationBatch, space: ActionSpace, rng: np.random.Generator) -> DecisionBatch:
        limit = self.max_ratio * obs["expected_annual_revenue"]
        room = np.maximum(0.0, limit - obs["loans"])
        return {"granted": np.minimum(obs["requested"].astype(float), room)}
