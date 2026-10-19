import numpy as np

from oikos.behavior.protocol import Box, Decider, ModelMeta
from oikos.markets import goods
from oikos.markets.labor import adjust_employment, workforce


def test_proportional_rationing_respects_stock_and_budgets():
    prices = np.array([10.0, 20.0])
    stock = np.array([5.0, 100.0])
    budgets = np.array([100.0, 100.0, 40.0])
    cand = np.array([[0, 1], [0, 1], [0, -1]])
    b, s, q = goods.clear_proportional(budgets, cand, prices, stock)
    sold = np.bincount(s, weights=q, minlength=2)
    spent = np.bincount(b, weights=q * prices[s], minlength=3)
    assert sold[0] <= 5.0 + 1e-9
    assert np.all(spent <= budgets + 1e-9)
    # seller 0 faces demand 10+10+4 units for 5 in stock: everyone gets the same fraction
    first = s == 0
    np.testing.assert_allclose(q[first] / (budgets[b[first]] / 10.0), 5.0 / 24.0)
    # buyers 0 and 1 spend the rest at seller 1; buyer 2 has no second candidate
    np.testing.assert_allclose(spent[:2], 100.0)
    assert spent[2] < 40.0


def test_random_queue_is_first_come_first_served():
    prices = np.array([10.0])
    stock = np.array([3.0])
    budgets = np.array([50.0, 50.0])
    cand = np.array([[0], [0]])
    b, s, q = goods.clear_random_queue(budgets, cand, prices, stock, np.random.default_rng(0))
    assert q.sum() <= 3.0 + 1e-9
    assert len(b) == 1  # the first buyer takes everything


def test_procurement_spreads_over_stock():
    s, q = goods.procure(300.0, np.array([True, True, False]), np.array([10.0, 10.0, 10.0]),
                         np.array([10.0, 30.0, 100.0]))
    assert list(s) == [0, 1]
    np.testing.assert_allclose(q, [7.5, 22.5])


def test_partner_update_switches_only_to_cheaper_sellers():
    rng = np.random.default_rng(1)
    partners = np.tile(np.array([0, 1]), (200, 1))
    prices = np.array([10.0, 10.0, 5.0, 50.0])
    new = goods.update_partners(partners, prices, np.zeros((200, 2), bool), 1.0, 0.0, 0.01, rng)
    assert set(np.unique(new)) <= {0, 1, 2}  # never switches to the more expensive seller 3
    assert (new == 2).any()


def test_layoff_cap_and_matching():
    rng = np.random.default_rng(0)
    employer = np.array([10] * 10 + [11] * 2 + [-1] * 8)
    employers = np.array([10, 11])
    fired, hired, unfilled = adjust_employment(employer, employers, np.array([2, 6]), np.array([3, 0]), rng)
    staff = workforce(employer, employers)
    assert fired[0] == 3 and staff[0] == 7          # cap of 3 layoffs binds
    assert hired[1] == 4 and staff[1] == 6           # vacancies filled from the pool
    assert unfilled.sum() == 0


def test_decider_clips_and_counts_invalid_actions():
    class Bad:
        meta = ModelMeta("bad", "0", "rule", True)

        def decide(self, obs, space, rng):
            return {"x": np.array([-1.0, 0.5, np.nan, 3.0])}

    d = Decider(Bad())
    out = d({"a": np.zeros(4)}, {"x": Box(0.0, 1.0)}, np.random.default_rng(0))
    np.testing.assert_allclose(out["x"], [0.0, 0.5, 0.0, 1.0])
    assert d.stats.invalid_actions == 3
