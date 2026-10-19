import numpy as np
import pytest

from oikos.core.ledger import InvariantViolation, Layout, Ledger, LedgerError

LAY = Layout(n_households=3, n_firms=2, n_energy=1)
H0, H1, H2 = 0, 1, 2
F0, F1 = 3, 4
GOV, ROW, BANK = LAY.government, LAY.rest_of_world, LAY.bank


def make_ledger() -> Ledger:
    led = Ledger(LAY)
    dep = np.zeros(LAY.n, dtype=np.int64)
    loans = np.zeros(LAY.n, dtype=np.int64)
    dep[[H0, H1, H2]] = [1000, 2000, 3000]
    dep[F0] = 500
    loans[F0] = 4000
    loans[GOV] = 3000
    led.open_balances(dep, loans)
    led.begin_period(0)
    return led


def test_opening_balance_sheet_consistent():
    led = make_ledger()
    assert led.bank_equity == 7000 - 6500
    led.check_invariants()


def test_payment_moves_deposits_without_creating_money():
    led = make_ledger()
    m0 = led.money_stock()
    led.pay([H0, H1], [F0, F0], [100, 200], "consumption")
    assert led.deposits[F0] == 800 and led.deposits[H0] == 900
    assert led.money_stock() == m0
    led.check_invariants()


def test_loan_creates_deposit_and_repayment_destroys_it():
    led = make_ledger()
    m0 = led.money_stock()
    led.lend([F1], [1500])
    assert led.loans[F1] == 1500 and led.deposits[F1] == 1500
    assert led.money_stock() == m0 + 1500
    led.repay([F1], [1000])
    assert led.loans[F1] == 500 and led.money_stock() == m0 + 500
    assert led.money_created == 1500 and led.money_destroyed == 1000
    led.check_invariants()


def test_interest_to_bank_destroys_money_and_raises_equity():
    led = make_ledger()
    eq0, m0 = led.bank_equity, led.money_stock()
    led.pay([F0], [BANK], [50], "loan_interest")
    assert led.bank_equity == eq0 + 50 and led.money_stock() == m0 - 50
    led.pay([BANK], [H2], [20], "deposit_interest")
    assert led.bank_equity == eq0 + 30 and led.money_stock() == m0 - 30
    led.check_invariants()


def test_write_off_reduces_bank_equity_not_deposits():
    led = make_ledger()
    eq0, m0 = led.bank_equity, led.money_stock()
    led.write_off([F0], [400])
    assert led.loans[F0] == 3600 and led.bank_equity == eq0 - 400 and led.money_stock() == m0
    led.check_invariants()


def test_overdraft_is_rejected():
    led = make_ledger()
    with pytest.raises(LedgerError):
        led.pay([H0], [F0], [1001], "consumption")
    # a payer appearing several times is checked on its total
    with pytest.raises(LedgerError):
        led.pay([H0, H0], [F0, F1], [600, 600], "consumption")


def test_float_amounts_are_rejected():
    led = make_ledger()
    with pytest.raises(LedgerError):
        led.pay([H0], [F0], [1.5], "consumption")


def test_repayment_above_loan_is_rejected():
    led = make_ledger()
    with pytest.raises(LedgerError):
        led.repay([H0], [10])


def test_tampering_is_detected():
    led = make_ledger()
    led.deposits[H0] += 1  # money appears without a counter-entry
    with pytest.raises(InvariantViolation):
        led.check_invariants()


def test_flow_journal_matches_deposit_changes():
    led = make_ledger()
    led.pay([H0], [F0], [100], "consumption")
    led.pay([F0], [GOV], [30], "profit_tax")
    led.lend([GOV], [500])
    led.pay([GOV], [ROW], [200], "purchase")
    led.check_invariants()  # includes the transaction-flow-matrix check (I7)
    flows = led.flow_matrix()
    assert flows["consumption"] == {"households->firms": 100}
    assert flows["loan_issue"] == {"bank->government": 500}
