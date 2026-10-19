"""Double-entry ledger for monetary stocks and flows.

All amounts are integer cents (int64). There is exactly one bank; every
non-bank entity holds a deposit account at it and may owe it a loan.

Balance sheets
--------------
non-bank entity i:  assets = deposits[i]          liabilities = loans[i]
bank:               assets = sum(loans)           liabilities = sum(deposits)
                    equity = assets - liabilities

Money (deposits) is created when the bank lends or pays out (interest,
dividends) and destroyed when loans are repaid or entities pay the bank
(interest). Write-offs reduce bank assets and equity without touching
deposits. These rules are enforced here and checked by
:meth:`Ledger.check_invariants` after every simulated period.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np


class LedgerError(RuntimeError):
    """Raised on an invalid posting (e.g. insufficient deposits)."""


class InvariantViolation(RuntimeError):
    """Raised when a stock-flow consistency invariant does not hold."""


@dataclass(frozen=True)
class Layout:
    """Index ranges of all entities in the global account arrays."""

    n_households: int
    n_firms: int
    n_energy: int

    @property
    def households(self) -> slice:
        return slice(0, self.n_households)

    @property
    def firms(self) -> slice:
        start = self.n_households
        return slice(start, start + self.n_firms)

    @property
    def energy(self) -> slice:
        start = self.n_households + self.n_firms
        return slice(start, start + self.n_energy)

    @property
    def government(self) -> int:
        return self.n_households + self.n_firms + self.n_energy

    @property
    def rest_of_world(self) -> int:
        return self.government + 1

    @property
    def bank(self) -> int:
        return self.government + 2

    @property
    def n(self) -> int:
        return self.bank + 1

    def sector_of(self) -> np.ndarray:
        sec = np.empty(self.n, dtype=np.int8)
        sec[self.households] = SECTOR_HOUSEHOLDS
        sec[self.firms] = SECTOR_FIRMS
        sec[self.energy] = SECTOR_ENERGY
        sec[self.government] = SECTOR_GOVERNMENT
        sec[self.rest_of_world] = SECTOR_ROW
        sec[self.bank] = SECTOR_BANK
        return sec


SECTOR_HOUSEHOLDS, SECTOR_FIRMS, SECTOR_ENERGY, SECTOR_GOVERNMENT, SECTOR_ROW, SECTOR_BANK = range(6)
SECTOR_NAMES = ("households", "firms", "energy", "government", "rest_of_world", "bank")


def _as_index(x, n: int) -> np.ndarray:
    a = np.asarray(x, dtype=np.int64)
    return np.broadcast_to(a, (n,)) if a.ndim == 0 else a


def _as_amount(x) -> np.ndarray:
    a = np.atleast_1d(np.asarray(x))
    if a.dtype.kind == "f":
        raise LedgerError("amounts must be integer cents; round explicitly before posting")
    return a.astype(np.int64)


class Ledger:
    """Monetary accounts of all entities plus a per-period flow journal."""

    def __init__(self, layout: Layout):
        self.layout = layout
        self.sector = layout.sector_of()
        n = layout.n
        self.deposits = np.zeros(n, dtype=np.int64)
        self.loans = np.zeros(n, dtype=np.int64)
        # The bank's side is tracked independently so that the invariants
        # compare two separately maintained records, not one array with itself.
        self.bank_deposit_liabilities = 0
        self.bank_loan_assets = 0
        self.bank_equity = 0
        self.t = 0
        self._begin_state()

    def open_balances(self, deposits: np.ndarray, loans: np.ndarray) -> None:
        """Set opening balances. Bank equity is the residual loans - deposits
        and must be non-negative."""
        deposits = np.asarray(deposits, dtype=np.int64)
        loans = np.asarray(loans, dtype=np.int64)
        if deposits[self.layout.bank] or loans[self.layout.bank]:
            raise LedgerError("bank cannot hold an account at itself")
        if (deposits < 0).any() or (loans < 0).any():
            raise LedgerError("opening balances must be non-negative")
        self.deposits = deposits.copy()
        self.loans = loans.copy()
        self.bank_deposit_liabilities = int(deposits.sum())
        self.bank_loan_assets = int(loans.sum())
        self.bank_equity = self.bank_loan_assets - self.bank_deposit_liabilities
        if self.bank_equity < 0:
            raise LedgerError("opening balances imply negative bank equity")
        self._begin_state()

    # ------------------------------------------------------------------ period
    def _begin_state(self) -> None:
        self.flows: dict[tuple[str, int, int], int] = defaultdict(int)
        self.money_created = 0
        self.money_destroyed = 0
        self.bank_income = 0
        self.bank_expenses = 0
        self.write_offs = 0
        self._dep_start = self.deposits.copy()
        self._loans_start = self.loans.copy()
        self._equity_start = self.bank_equity

    def begin_period(self, t: int) -> None:
        self.t = t
        self._begin_state()

    # ---------------------------------------------------------------- postings
    def _journal(self, kind: str, src: np.ndarray, dst: np.ndarray, amt: np.ndarray) -> None:
        if amt.size == 0:
            return
        s = self.sector[src].astype(np.int64)
        d = self.sector[dst].astype(np.int64)
        key = s * 8 + d
        totals = np.zeros(64, dtype=np.int64)
        np.add.at(totals, key, amt)
        for k in np.nonzero(totals)[0]:
            self.flows[(kind, int(k // 8), int(k % 8))] += int(totals[k])

    def pay(self, payers, payees, amounts, kind: str) -> None:
        """Transfer deposits. Either side may be the bank (money is then
        destroyed or created and booked against bank equity)."""
        amt = _as_amount(amounts)
        n = amt.size
        src = _as_index(payers, n)
        dst = _as_index(payees, n)
        if src.shape != amt.shape or dst.shape != amt.shape:
            raise LedgerError("payers, payees and amounts must have matching shapes")
        if (amt < 0).any():
            raise LedgerError(f"negative amount in '{kind}'")
        keep = amt > 0
        src, dst, amt = src[keep], dst[keep], amt[keep]
        if amt.size == 0:
            return
        bank = self.layout.bank
        if ((src == bank) & (dst == bank)).any():
            raise LedgerError("bank cannot pay itself")

        out = np.zeros_like(self.deposits)
        np.add.at(out, src, amt)
        out[bank] = 0
        if (out > self.deposits).any():
            i = int(np.argmax(out - self.deposits))
            raise LedgerError(
                f"insufficient deposits for '{kind}': entity {i} has {self.deposits[i]}, needs {out[i]}"
            )

        from_bank = src == bank
        to_bank = dst == bank
        self.deposits -= out
        inflow = np.zeros_like(self.deposits)
        np.add.at(inflow, dst, amt)
        inflow[bank] = 0
        self.deposits += inflow

        created = int(amt[from_bank].sum())
        destroyed = int(amt[to_bank].sum())
        self.bank_deposit_liabilities += created - destroyed
        self.bank_equity += destroyed - created
        self.bank_income += destroyed
        self.bank_expenses += created
        self.money_created += created
        self.money_destroyed += destroyed
        self._journal(kind, src, dst, amt)

    def lend(self, borrowers, amounts, kind: str = "loan_issue") -> None:
        amt = _as_amount(amounts)
        idx = _as_index(borrowers, amt.size)
        if (amt < 0).any():
            raise LedgerError("negative loan")
        if (idx == self.layout.bank).any():
            raise LedgerError("bank cannot borrow from itself")
        np.add.at(self.loans, idx, amt)
        np.add.at(self.deposits, idx, amt)
        total = int(amt.sum())
        self.bank_loan_assets += total
        self.bank_deposit_liabilities += total
        self.money_created += total
        self._journal(kind, np.full(idx.size, self.layout.bank), idx, amt)

    def repay(self, borrowers, amounts, kind: str = "loan_repayment") -> None:
        amt = _as_amount(amounts)
        idx = _as_index(borrowers, amt.size)
        if (amt < 0).any():
            raise LedgerError("negative repayment")
        need = np.zeros_like(self.loans)
        np.add.at(need, idx, amt)
        if (need > self.loans).any() or (need > self.deposits).any():
            raise LedgerError("repayment exceeds loan or deposits")
        self.loans -= need
        self.deposits -= need
        total = int(amt.sum())
        self.bank_loan_assets -= total
        self.bank_deposit_liabilities -= total
        self.money_destroyed += total
        self._journal(kind, idx, np.full(idx.size, self.layout.bank), amt)

    def write_off(self, borrowers, amounts) -> None:
        amt = _as_amount(amounts)
        idx = _as_index(borrowers, amt.size)
        need = np.zeros_like(self.loans)
        np.add.at(need, idx, amt)
        if (need > self.loans).any() or (amt < 0).any():
            raise LedgerError("write-off exceeds loan")
        self.loans -= need
        total = int(amt.sum())
        self.bank_loan_assets -= total
        self.bank_equity -= total
        self.write_offs += total

    # ------------------------------------------------------------------ views
    def net_financial_worth(self) -> np.ndarray:
        nw = self.deposits - self.loans
        nw[self.layout.bank] = self.bank_equity
        return nw

    def money_stock(self) -> int:
        return int(self.deposits.sum())

    def sector_totals(self, values: np.ndarray) -> np.ndarray:
        out = np.zeros(6, dtype=np.int64)
        np.add.at(out, self.sector.astype(np.int64), values)
        return out

    # ------------------------------------------------------------- invariants
    def check_invariants(self) -> None:
        """Raise :class:`InvariantViolation` unless all accounting identities hold exactly."""
        bank = self.layout.bank
        errors = []
        if self.deposits[bank] != 0 or self.loans[bank] != 0:
            errors.append("bank holds an account at itself")
        if (self.deposits < 0).any():
            errors.append(f"negative deposits at {np.nonzero(self.deposits < 0)[0][:5].tolist()}")
        if (self.loans < 0).any():
            errors.append("negative loans")
        if int(self.deposits.sum()) != self.bank_deposit_liabilities:
            errors.append("I1: sum of deposits != bank deposit liabilities")
        if int(self.loans.sum()) != self.bank_loan_assets:
            errors.append("I2: sum of loans != bank loan assets")
        if self.bank_equity != self.bank_loan_assets - self.bank_deposit_liabilities:
            errors.append("I3: bank equity != loans - deposits")
        if int(self.net_financial_worth().sum()) != 0:
            errors.append("I4: financial net worth does not sum to zero")
        d_money = int(self.deposits.sum() - self._dep_start.sum())
        if d_money != self.money_created - self.money_destroyed:
            errors.append("I5: change in money stock != created - destroyed")
        d_equity = self.bank_equity - self._equity_start
        if d_equity != self.bank_income - self.bank_expenses - self.write_offs:
            errors.append("I6: change in bank equity != income - expenses - write-offs")
        # I7: per sector, change in deposits equals journal inflows - outflows
        # (loan issue counts as inflow, repayment as outflow).
        net = np.zeros(6, dtype=np.int64)
        for (_, s, d), v in self.flows.items():
            net[s] -= v
            net[d] += v
        d_dep = self.sector_totals(self.deposits - self._dep_start)
        d_dep[SECTOR_BANK] = -(self.money_created - self.money_destroyed)
        if not np.array_equal(net, d_dep):
            errors.append(f"I7: transaction-flow matrix inconsistent: {net.tolist()} vs {d_dep.tolist()}")
        if errors:
            raise InvariantViolation(f"t={self.t}: " + "; ".join(errors))

    def flow_matrix(self) -> dict[str, dict[str, int]]:
        """Flows of the current period by kind as {kind: {'from->to': cents}}."""
        out: dict[str, dict[str, int]] = defaultdict(dict)
        for (kind, s, d), v in sorted(self.flows.items()):
            out[kind][f"{SECTOR_NAMES[s]}->{SECTOR_NAMES[d]}"] = v
        return dict(out)
