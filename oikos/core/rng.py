"""Named random streams for common random numbers (CRN).

Every random draw comes from a generator keyed by (run seed, purpose, period).
Two scenarios run with the same seed therefore see identical draws for the
same purpose in the same period, even if earlier periods consumed a
different number of draws. This keeps scenario comparisons paired.
"""

from __future__ import annotations

import zlib

import numpy as np


class Streams:
    def __init__(self, seed: int):
        self.seed = int(seed)

    def get(self, purpose: str, t: int = 0) -> np.random.Generator:
        key = zlib.crc32(purpose.encode("utf-8"))
        # Periods may be negative (burn-in); shift into the non-negative range.
        return np.random.default_rng([self.seed, key, t + 1_000_000])
