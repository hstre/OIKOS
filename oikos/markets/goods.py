"""Goods market protocols. No equilibrium is assumed: buyers visit a few
sellers, sellers sell from stock at posted prices, and excess demand is
rationed by an explicit protocol.

All functions return (buyer, seller, quantity) trade records; payments are
posted by the caller so that every transaction goes through the ledger.
"""

from __future__ import annotations

import numpy as np


def update_partners(partners: np.ndarray, prices: np.ndarray, rationed: np.ndarray,
                    p_price: float, p_quantity: float, min_gain: float,
                    rng: np.random.Generator) -> np.ndarray:
    """Persistent trading relationships (after Lengnick 2013).

    partners: (n_buyers, k) seller indices, modified copy is returned.
    With probability p_price a buyer compares a random partner with a random
    non-partner and switches if the newcomer is cheaper by more than min_gain.
    With probability p_quantity a buyer that was rationed by a partner
    replaces that partner by a random non-partner.
    """
    partners = partners.copy()
    n, k = partners.shape
    n_sellers = prices.size

    def random_outsiders(rows: np.ndarray) -> np.ndarray:
        cand = rng.integers(0, n_sellers, rows.size)
        clash = (partners[rows] == cand[:, None]).any(axis=1)
        # one redraw; remaining clashes simply keep their partner
        cand[clash] = rng.integers(0, n_sellers, int(clash.sum()))
        ok = ~(partners[rows] == cand[:, None]).any(axis=1)
        return np.where(ok, cand, -1)

    rows = np.nonzero(rng.random(n) < p_price)[0]
    if rows.size:
        slot = rng.integers(0, k, rows.size)
        new = random_outsiders(rows)
        old = partners[rows, slot]
        better = (new >= 0) & (prices[np.maximum(new, 0)] < prices[old] * (1 - min_gain))
        partners[rows[better], slot[better]] = new[better]

    if rationed.any():
        r_rows, r_slot = np.nonzero(rationed)
        pick = rng.random(r_rows.size) < p_quantity
        r_rows, r_slot = r_rows[pick], r_slot[pick]
        _, first = np.unique(r_rows, return_index=True)  # at most one replacement per buyer
        r_rows, r_slot = r_rows[first], r_slot[first]
        if r_rows.size:
            new = random_outsiders(r_rows)
            ok = new >= 0
            partners[r_rows[ok], r_slot[ok]] = new[ok]
    return partners


def sort_by_price(partners: np.ndarray, prices: np.ndarray) -> np.ndarray:
    order = np.argsort(prices[partners], axis=1, kind="stable")
    return np.take_along_axis(partners, order, axis=1)


def rationed_by(unsatisfied: np.ndarray, sold_out: np.ndarray, partners: np.ndarray) -> np.ndarray:
    """Mask (n_buyers, k): the buyer left budget unspent and partner j ran out of stock."""
    return unsatisfied[:, None] & sold_out[partners]


def candidate_sellers(n_buyers: int, active: np.ndarray, prices: np.ndarray, k: int,
                      rng: np.random.Generator) -> np.ndarray:
    """Each buyer samples k distinct active sellers, sorted by price (cheapest first).
    Returns an (n_buyers, k) array of seller indices, -1 where fewer than k exist."""
    ids = np.nonzero(active)[0]
    k_eff = min(k, ids.size)
    out = np.full((n_buyers, k), -1, dtype=np.int64)
    if k_eff == 0:
        return out
    keys = rng.random((n_buyers, ids.size))
    picks = ids[np.argsort(keys, axis=1)[:, :k_eff]]
    order = np.argsort(prices[picks], axis=1, kind="stable")
    out[:, :k_eff] = np.take_along_axis(picks, order, axis=1)
    return out


def clear_proportional(budgets: np.ndarray, candidates: np.ndarray, prices: np.ndarray,
                       stock: np.ndarray):
    """Round r: every buyer with budget left asks its r-th candidate for
    budget/price units. A seller facing more demand than stock serves all
    its buyers in the same proportion. Order-independent and deterministic."""
    remaining = budgets.astype(float).copy()
    stock = stock.astype(float).copy()
    n_sellers = stock.size
    records = []
    for r in range(candidates.shape[1]):
        f = candidates[:, r]
        ask = (remaining > 0) & (f >= 0)
        if not ask.any():
            break
        b = np.nonzero(ask)[0]
        s = f[ask]
        want = remaining[b] / prices[s]
        demand = np.bincount(s, weights=want, minlength=n_sellers)
        fill = np.divide(stock, demand, out=np.zeros(n_sellers), where=demand > 0)
        fill = np.minimum(1.0, fill)
        q = want * fill[s]
        sold = np.bincount(s, weights=q, minlength=n_sellers)
        stock = np.maximum(0.0, stock - sold)
        remaining[b] -= q * prices[s]
        remaining = np.maximum(remaining, 0.0)
        pos = q > 0
        records.append((b[pos], s[pos], q[pos]))
    return _concat(records)


def clear_random_queue(budgets: np.ndarray, candidates: np.ndarray, prices: np.ndarray,
                       stock: np.ndarray, rng: np.random.Generator):
    """Buyers arrive in random order and buy as much as they can from their
    candidates in price order (first come, first served)."""
    remaining = budgets.astype(float).copy()
    stock = stock.astype(float).copy()
    bs, ss, qs = [], [], []
    for b in rng.permutation(budgets.size):
        for s in candidates[b]:
            if s < 0 or remaining[b] <= 0:
                break
            q = min(remaining[b] / prices[s], stock[s])
            if q <= 0:
                continue
            stock[s] -= q
            remaining[b] -= q * prices[s]
            bs.append(b)
            ss.append(s)
            qs.append(q)
    return np.asarray(bs, dtype=np.int64), np.asarray(ss, dtype=np.int64), np.asarray(qs, dtype=float)


def procure(budget: float, active: np.ndarray, prices: np.ndarray, stock: np.ndarray):
    """Institutional buyer (government, rest of world): spreads its budget over
    all active sellers in proportion to their remaining stock (one round)."""
    stock = np.where(active, stock, 0.0)
    total = stock.sum()
    if budget <= 0 or total <= 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0)
    s = np.nonzero(stock > 0)[0]
    q = np.minimum(stock[s], budget * stock[s] / total / prices[s])
    return s, q


def _concat(records):
    if not records:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64), np.zeros(0)
    b, s, q = zip(*records)
    return np.concatenate(b), np.concatenate(s), np.concatenate(q)
