"""OIKOS v0.1 economy: households, goods firms, energy suppliers, one bank,
a government and the rest of the world, simulated in monthly periods.

The order of events within a period is part of the institutional setup and
is documented in docs/02_modell_v0_1.md. Every monetary transaction goes
through the ledger; all accounting identities are checked at the end of
each period and a violation aborts the run.
"""

from __future__ import annotations

import numpy as np

from .behavior.protocol import Decider
from .behavior.rules.bank import LeverageCreditRule
from .behavior.rules.firm import EnergySupplierRule, FirmPlanningRule
from .behavior.rules.household import HouseholdBudgetRule
from .core.ledger import Layout, Ledger
from .core.physical import PhysicalAccounts
from .core.rng import Streams
from .institutions.credit import apply_capital_requirement
from .institutions.energy_policy import EnergyPolicy
from .institutions.fiscal import FiscalRules
from .markets import goods as goods_market
from .markets.labor import adjust_employment, workforce
from . import metrics as M

EUR = 100  # cents


def _floor_int(x) -> np.ndarray:
    return np.floor(np.asarray(x, dtype=float)).astype(np.int64)


class Economy:
    def __init__(self, cfg: dict, seed: int, models: dict | None = None):
        self.cfg = cfg
        self.seed = int(seed)
        self.streams = Streams(seed)
        models = models or {}
        hc, fc, ec, bc = cfg["households"], cfg["firms"], cfg["energy"], cfg["bank"]
        self.H, self.F, self.E = int(hc["n"]), int(fc["n"]), int(ec["n"])
        self.layout = Layout(self.H, self.F, self.E)
        self.ledger = Ledger(self.layout)
        self.phys = PhysicalAccounts()
        self.fiscal = FiscalRules(cfg["government"])
        self.policy = EnergyPolicy(cfg["policy"], self.H)
        self.inst = cfg["institutions"]

        self.household_model = Decider(models.get("household") or HouseholdBudgetRule(hc["min_energy_share"]))
        self.firm_model = Decider(models.get("firm") or FirmPlanningRule(fc))
        self.energy_model = Decider(models.get("energy") or EnergySupplierRule(ec))
        self.credit_model = Decider(models.get("credit") or LeverageCreditRule(bc["max_debt_to_annual_revenue"]))

        self.t = -int(cfg["simulation"]["burn_in_months"])
        self.t_end = int(cfg["simulation"]["horizon_months"])
        self.records: list[dict] = []
        self.flags: dict[str, int] = {"bank_negative_equity_months": 0, "overdraft_events": 0}
        self._init_state()

    # ================================================================== setup
    def _init_state(self) -> None:
        cfg, rng = self.cfg, self.streams.get("init")
        hc, fc, ec, gc, bc = cfg["households"], cfg["firms"], cfg["energy"], cfg["government"], cfg["bank"]
        H, F, E, lay = self.H, self.F, self.E, self.layout

        # households
        d = hc["initial_deposits_eur"]
        dep_h = _floor_int(rng.lognormal(np.log(d["median"] * EUR), d["sigma"], H))
        n = hc["energy_need_kwh"]
        self.need_base = rng.lognormal(np.log(n["median"]), n["sigma"], H)
        self.efficiency = np.ones(H)
        self.retrofit_at = np.full(H, np.iinfo(np.int64).max)
        self.retrofitted = np.zeros(H, dtype=bool)
        ci, cw = hc["consumption_propensity_income"], hc["consumption_propensity_wealth"]
        self.c_income = rng.uniform(ci["low"], ci["high"], H)
        self.c_wealth = rng.uniform(cw["low"], cw["high"], H)
        el = hc["energy_price_elasticity"]
        self.elasticity = np.clip(rng.normal(el["mean"], el["sd"], H), el["low"], el["high"])
        self.supplier = rng.integers(0, E, H)
        self.capital_income = np.zeros(H, dtype=np.int64)
        self.net_income = np.zeros(H, dtype=np.int64)
        self.income_hist = np.zeros((12, H), dtype=np.int64)
        self.quintile = np.zeros(H, dtype=np.int64)

        # energy suppliers
        self.world_price_base = ec["world_price_eur_per_kwh"] * EUR      # cents/kWh
        wage0 = int(fc["initial_wage_eur"] * EUR)
        self.e_markup = float(ec["markup"])
        self.labor_per_kwh = float(ec["labor_per_kwh"])
        e_price0 = (self.world_price_base + wage0 * self.labor_per_kwh) * (1 + self.e_markup)
        self.e_price = np.full(E, e_price0)
        q_hh0 = float((self.need_base).sum())

        # employment and goods firms
        self.prod = float(fc["productivity"])
        self.eps = float(fc["energy_intensity"])
        employed0 = int(round(0.94 * H))
        q_firm_guess = employed0 * self.prod * self.eps
        e_workers = np.full(E, int(np.ceil((q_hh0 + q_firm_guess) / E * self.labor_per_kwh)))
        f_workers_total = employed0 - int(e_workers.sum())
        f_workers = np.full(F, f_workers_total // F)
        f_workers[: f_workers_total % F] += 1

        self.employer = np.full(H, -1, dtype=np.int64)
        order = rng.permutation(H)
        pos = 0
        producers = np.arange(lay.firms.start, lay.energy.stop)
        for p, w in zip(producers, np.concatenate([f_workers, e_workers])):
            self.employer[order[pos:pos + w]] = p
            pos += w
        self.producers = producers

        self.wage = np.full(F + E, wage0, dtype=np.int64)
        self.markup = np.full(F, float(fc["initial_markup"]))
        self.expected_sales = f_workers * self.prod
        self.last_sales = self.expected_sales.astype(float).copy()
        self.inventory = fc["inventory_target"] * self.expected_sales.astype(float)
        self.unit_cost = wage0 / self.prod + self.eps * e_price0
        self.price = np.full(F, self.unit_cost * (1 + fc["initial_markup"]))
        self.inv_value = self.inventory * self.unit_cost
        self.unfilled = np.zeros(F)
        self.months_all_filled = np.zeros(F)
        k = int(self.inst["goods_market_visits"])
        self.partners = np.argsort(rng.random((H, F)), axis=1)[:, :k]
        self.e_expected = np.full(E, (q_hh0 + q_firm_guess) / E)
        self.e_last_sales = self.e_expected.copy()

        # ownership: richest households own all producers and the bank
        owners = np.argsort(-dep_h)[: max(1, int(hc["owner_share"] * H))]
        k = min(int(hc["owners_per_firm"]), owners.size)
        self.owners = [rng.choice(owners, size=k, replace=False) for _ in range(F + E)]
        self.bank_owners = owners

        # opening balance sheets
        deposits = np.zeros(lay.n, dtype=np.int64)
        loans = np.zeros(lay.n, dtype=np.int64)
        deposits[lay.households] = dep_h
        wage_bill_f = f_workers * wage0
        deposits[lay.firms] = _floor_int(fc["initial_deposits_months"] * wage_bill_f)
        loans[lay.firms] = _floor_int(fc["initial_loans_months"] * wage_bill_f)
        e_cost = e_workers * wage0 + self.e_expected * self.world_price_base
        deposits[lay.energy] = _floor_int(e_cost)
        deposits[lay.government] = int(gc["initial_deposits_eur"] * EUR)
        imports0 = (q_hh0 + q_firm_guess) * self.world_price_base
        deposits[lay.rest_of_world] = int(imports0 / cfg["rest_of_world"]["spending_rate"])
        eq_share = float(bc["initial_equity_share_of_loans"])
        total_loans = deposits.sum() / (1 - eq_share)
        loans[lay.government] = int(total_loans) - int(loans.sum())
        if loans[lay.government] < 0:
            raise ValueError("opening balances: private loans exceed what deposits and bank equity allow")
        self.ledger.open_balances(deposits, loans)

        unemployed0 = H - employed0
        self.avg_wage = float(wage0)
        self.fiscal_fallback = int(
            self.fiscal.income_tax_rate * employed0 * wage0
            - unemployed0 * self.fiscal.benefit(wage0)
            - loans[lay.government] * bc["loan_rate_annual"] / 12
        )
        self.cum = {"retrofits": 0, "firm_exits": 0, "policy_cost": 0}
        self.e_price_prev = self.e_price.copy()
        self.hh_energy_prev = q_hh0

    # ============================================================ exogenous
    def world_price(self, t: int) -> float:
        s = self.cfg["shock"]
        if s["start_month"] <= t < s["start_month"] + s["duration_months"]:
            return self.world_price_base * float(s["world_price_factor"])
        return self.world_price_base

    # ============================================================== helpers
    def _ensure_funds(self, entity: int, amount: int, kind: str = "overdraft") -> None:
        """Automatic credit line (government always; producers for
        unavoidable payments such as interest or imports, counted as flag)."""
        short = int(amount) - int(self.ledger.deposits[entity])
        if short > 0:
            self.ledger.lend([entity], [short], kind=kind)
            if entity != self.layout.government:
                self.flags["overdraft_events"] += 1

    def _pay_dividends(self, payers: np.ndarray, amounts: np.ndarray, owner_lists: list,
                       kind: str) -> np.ndarray:
        """Distribute dividends equally among owners, withholding income tax.
        Returns net dividend income per household."""
        L, gov = self.ledger, self.layout.government
        income = np.zeros(self.H, dtype=np.int64)
        src, dst, amt = [], [], []
        for payer, total, owners in zip(payers, amounts, owner_lists):
            per_owner = int(total) // owners.size
            if per_owner <= 0:
                continue
            tax = int(per_owner * self.fiscal.income_tax_rate)
            src += [payer] * owners.size
            dst += owners.tolist()
            amt += [per_owner - tax] * owners.size
            src.append(payer)
            dst.append(gov)
            amt.append(tax * owners.size)
        if amt:
            src_a, dst_a, amt_a = np.array(src), np.array(dst), np.array(amt, dtype=np.int64)
            hh = dst_a != gov
            L.pay(src_a[hh], dst_a[hh], amt_a[hh], kind)
            L.pay(src_a[~hh], dst_a[~hh], amt_a[~hh], "dividend_tax")
            np.add.at(income, dst_a[hh], amt_a[hh])
            self._period["taxes"] += int(amt_a[~hh].sum())
        return income

    # ================================================================= step
    def step(self) -> dict:
        t, L, lay, cfg = self.t, self.ledger, self.layout, self.cfg
        H, F, E = self.H, self.F, self.E
        hc, fc, bc, inst = cfg["households"], cfg["firms"], cfg["bank"], self.inst
        gov, row, bank = lay.government, lay.rest_of_world, lay.bank
        firm_ids = np.arange(lay.firms.start, lay.firms.stop)
        energy_ids = np.arange(lay.energy.start, lay.energy.stop)
        L.begin_period(t)
        self.phys.begin_period(t, float(self.inventory.sum()))
        self._period = {"taxes": 0, "benefits": 0, "gov_interest": 0, "transfers": 0,
                        "subsidy": 0, "investment": 0, "gov_purchases": 0, "exports": 0}
        revenue = np.zeros(F + E)
        input_cost = np.zeros(F + E)
        interest_paid = np.zeros(F + E)

        # ---- 1 exogenous world price, policy budget, retrofits taking effect
        p_world = self.world_price(t)
        if t == self.policy.start:
            increase = (p_world - self.world_price_base) * (1 + self.e_markup)
            self.policy.fix_budget(increase, self.hh_energy_prev, self.e_price_prev)
        done = self.retrofit_at == t
        self.efficiency[done] *= 1 - self.policy.need_reduction
        need = self.need_base * self.efficiency

        # ---- 2 energy suppliers: expectations, staffing, cost-plus price
        dec = self.energy_model({"expected_sales": self.e_expected, "last_sales": self.e_last_sales},
                                EnergySupplierRule.action_space({}), self.streams.get("energy_plan", t))
        self.e_expected = dec["expected_sales"]
        e_target = dec["target_workers"]
        self.e_price = (p_world + self.wage[F:] * self.labor_per_kwh) * (1 + self.e_markup)
        cheapest = int(np.argmin(self.e_price))
        p_e_firms = float(self.e_price[cheapest])

        # ---- 3 goods firms: expectations, output plan, markup, wage
        obs = {"inventory": self.inventory, "expected_sales": self.expected_sales.astype(float),
               "last_sales": self.last_sales, "markup": self.markup, "wage": self.wage[:F].astype(float),
               "productivity": np.full(F, self.prod), "unfilled_vacancies": self.unfilled,
               "months_all_filled": self.months_all_filled}
        dec = self.firm_model(obs, self.firm_model.model.action_space(obs), self.streams.get("firm_plan", t))
        self.expected_sales = dec["expected_sales"]
        self.markup = dec["markup"]
        self.wage[:F] = _floor_int(dec["wage"])
        f_target = dec["target_workers"]
        self.wage[F:] = int(self.wage[:F].mean())  # energy sector follows the average goods-sector wage
        self.unit_cost = self.wage[:F] / self.prod + self.eps * p_e_firms
        self.price = self.unit_cost * (1 + self.markup)

        # ---- 4 financing of the planned wage and input bill
        target = np.concatenate([f_target, e_target])
        cost_per_worker = self.wage.astype(float).copy()
        cost_per_worker[:F] += self.prod * self.eps * p_e_firms
        dep = L.deposits[self.producers].astype(float)
        need_cash = target * cost_per_worker
        requested = np.maximum(0.0, np.ceil(need_cash - dep))
        exp_rev = np.concatenate([self.expected_sales * self.price, self.e_expected * self.e_price])
        cobs = {"requested": requested, "loans": L.loans[self.producers].astype(float),
                "expected_annual_revenue": 12 * exp_rev}
        granted = self.credit_model(cobs, LeverageCreditRule.action_space(cobs), self.streams.get("credit", t))["granted"]
        private_loans = int(L.loans[self.producers].sum())
        granted = apply_capital_requirement(np.floor(granted), L.bank_equity, private_loans, inst["min_capital_ratio"])
        L.lend(self.producers, granted.astype(np.int64))
        affordable = np.floor(L.deposits[self.producers] / cost_per_worker)

        # ---- 5 labour market
        # Layoffs are limited per month (employment protection), except where
        # an employer cannot pay its staff: then it sheds down to what it can pay.
        current = workforce(self.employer, self.producers)
        layoff_cap = np.ceil(inst["max_layoff_share_per_month"] * current)
        target = np.minimum(np.maximum(target, current - layoff_cap), affordable)
        _, _, unfilled = adjust_employment(self.employer, self.producers, target, current,
                                           self.streams.get("labor", t),
                                           inst["job_separation_rate"], inst["job_search_rate"])
        staff = workforce(self.employer, self.producers)
        if (staff > affordable).any():
            raise RuntimeError("employer holds more workers than it can pay")
        self.unfilled = unfilled[:F].astype(float)
        self.months_all_filled = np.where(unfilled[:F] > 0, 0, self.months_all_filled + 1)

        # ---- 6 production; firms buy energy
        output = staff[:F] * self.prod
        e_firms_kwh = output * self.eps
        e_bill = _floor_int(e_firms_kwh * p_e_firms)
        L.pay(firm_ids, np.full(F, energy_ids[cheapest]), e_bill, "energy_firms")
        input_cost[:F] += e_bill
        revenue[F + cheapest] += e_bill.sum()
        e_sales = np.zeros(E)
        e_sales[cheapest] += e_firms_kwh.sum()
        self.inventory = self.inventory + output
        self.phys.add("goods_produced", output.sum())
        self.phys.add("energy_used_firms", e_firms_kwh.sum())

        # ---- 7 wages, benefits, transfers
        wealth_before_income = L.deposits[:H].copy()
        emp = np.nonzero(self.employer >= 0)[0]
        local = self.employer[emp] - lay.firms.start
        gross = self.wage[local]
        tax = self.fiscal.income_tax(gross)
        L.pay(self.employer[emp], emp, gross - tax, "wages")
        L.pay(self.employer[emp], np.full(emp.size, gov), tax, "income_tax")
        self._period["taxes"] += int(tax.sum())
        wage_cost = np.bincount(local, weights=gross, minlength=F + E)
        income = np.zeros(H, dtype=np.int64)
        income[emp] = gross - tax
        self.avg_wage = float(gross.mean()) if emp.size else self.avg_wage

        unemp = np.nonzero(self.employer < 0)[0]
        benefit = self.fiscal.benefit(self.avg_wage)
        if unemp.size and benefit > 0:
            self._ensure_funds(gov, benefit * unemp.size)
            L.pay(np.full(unemp.size, gov), unemp, np.full(unemp.size, benefit), "unemployment_benefit")
            income[unemp] += benefit
            self._period["benefits"] = benefit * unemp.size

        transfer = self.policy.transfer_per_household(t)
        if transfer > 0:
            self._ensure_funds(gov, transfer * H)
            L.pay(np.full(H, gov), np.arange(H), np.full(H, transfer), "policy_transfer")
            income += transfer
            self._period["transfers"] = transfer * H

        # ---- 8 household budget decision; energy purchases
        p_supplier = self.e_price[self.supplier]
        p_hh = self.policy.household_price(self.e_price, t)[self.supplier]
        net_income = income + self.capital_income
        hobs = {"need_kwh": need, "energy_price": p_hh, "reference_price": self.p_ref,
                "deposits": L.deposits[:H], "net_income": net_income.astype(float),
                "wealth_before_income": wealth_before_income.astype(float),
                "c_income": self.c_income, "c_wealth": self.c_wealth, "elasticity": self.elasticity}
        hdec = self.household_model(hobs, HouseholdBudgetRule.action_space(hobs), self.streams.get("household", t))
        e_kwh = hdec["energy_kwh"]
        e_pay = np.minimum(_floor_int(e_kwh * p_hh), L.deposits[:H])
        L.pay(np.arange(H), energy_ids[self.supplier], e_pay, "energy_households")
        sub = _floor_int(e_kwh * (p_supplier - p_hh))
        if sub.sum() > 0:
            self._ensure_funds(gov, int(sub.sum()))
            L.pay(np.full(H, gov), energy_ids[self.supplier], sub, "energy_subsidy")
            self._period["subsidy"] = int(sub.sum())
        revenue[F:] += np.bincount(self.supplier, weights=e_pay + sub, minlength=E)
        e_sales += np.bincount(self.supplier, weights=e_kwh, minlength=E)
        self.phys.add("energy_used_households", e_kwh.sum())
        forced = e_kwh < hdec["energy_wanted"] * (1 - 1e-9)
        self.p_ref = self.p_ref + hc["reference_price_adaptation"] * (p_hh - self.p_ref)
        switch = self.streams.get("supplier_switch", t).random(H) < hc["supplier_switch_rate"]
        self.supplier = np.where(switch, int(np.argmin(self.e_price)), self.supplier)

        # ---- 9 goods market: households, then government and rest of world
        stock = self.inventory.copy()
        budgets = np.minimum(_floor_int(hdec["goods_budget"]), L.deposits[:H])
        rng_g = self.streams.get("goods_market", t)
        cand = goods_market.sort_by_price(self.partners, self.price)
        if inst["goods_market_protocol"] == "proportional":
            b, s, q = goods_market.clear_proportional(budgets, cand, self.price, stock)
        elif inst["goods_market_protocol"] == "random_queue":
            b, s, q = goods_market.clear_random_queue(budgets, cand, self.price, stock, rng_g)
        else:
            raise ValueError(f"unknown goods market protocol {inst['goods_market_protocol']!r}")
        pay = _floor_int(q * self.price[s])
        L.pay(b, firm_ids[s], pay, "consumption")
        sold = np.bincount(s, weights=q, minlength=F)
        stock -= sold
        revenue[:F] += np.bincount(s, weights=pay, minlength=F)
        goods_hh = np.bincount(b, weights=q, minlength=H)
        spend_hh = np.bincount(b, weights=pay, minlength=H)
        unsatisfied = budgets - spend_hh > 0.01 * np.maximum(budgets, 1)
        sold_out = stock <= 1e-9 * np.maximum(self.inventory, 1.0)
        self.partners = goods_market.update_partners(
            self.partners, self.price, goods_market.rationed_by(unsatisfied, sold_out, self.partners),
            inst["partner_search_price"], inst["partner_search_quantity"], inst["partner_min_price_gain"],
            self.streams.get("partner_search", t))

        def institutional_purchase(buyer: int, budget: int, kind: str) -> int:
            nonlocal stock, sold
            s_, q_ = goods_market.procure(budget, np.ones(F, bool), self.price, stock)
            pay_ = _floor_int(q_ * self.price[s_])
            L.pay(np.full(s_.size, buyer), firm_ids[s_], pay_, kind)
            np.subtract.at(stock, s_, q_)
            np.add.at(sold, s_, q_)
            np.add.at(revenue, s_, pay_)
            return int(pay_.sum())

        g_budget = self.fiscal.purchases(self.fiscal_fallback)
        self._ensure_funds(gov, g_budget)
        self._period["gov_purchases"] = institutional_purchase(gov, g_budget, "government_purchases")
        inv_budget = self.policy.investment_budget(t)
        if inv_budget > 0:
            self._ensure_funds(gov, inv_budget)
            spent = institutional_purchase(gov, inv_budget, "public_investment")
            self._period["investment"] = spent
            n_new = self.policy.retrofits_from(spent)
            if n_new:
                cand_h = np.nonzero(~self.retrofitted)[0]
                pick = cand_h[np.argsort(-need[cand_h], kind="stable")[:n_new]]
                self.retrofitted[pick] = True
                self.retrofit_at[pick] = t + self.policy.lag
                self.cum["retrofits"] += pick.size
        row_budget = int(cfg["rest_of_world"]["spending_rate"] * L.deposits[row])
        self._period["exports"] = institutional_purchase(row, row_budget, "exports")
        stock = np.maximum(stock, 0.0)
        self.phys.add("goods_sold", float(sold.sum()))
        self.last_sales = sold
        depreciation = stock * fc["inventory_depreciation"]
        self.inventory = stock - depreciation
        self.phys.add("goods_depreciated", float(depreciation.sum()))

        # ---- 10 energy suppliers pay for imported primary energy
        import_bill = _floor_int(e_sales * p_world)
        for k in range(E):
            self._ensure_funds(int(energy_ids[k]), int(import_bill[k]))
        L.pay(energy_ids, np.full(E, row), import_bill, "energy_imports")
        input_cost[F:] += import_bill
        self.phys.add("energy_imported", float(e_sales.sum()))
        self.e_last_sales = e_sales

        # ---- 11 interest and repayment
        borrowers = np.nonzero(L.loans > 0)[0]
        due = _floor_int(L.loans[borrowers] * bc["loan_rate_annual"] / 12)
        for i, a in zip(borrowers, due):
            self._ensure_funds(int(i), int(a), kind="interest_capitalised")
        L.pay(borrowers, np.full(borrowers.size, bank), due, "loan_interest")
        is_prod = (borrowers >= lay.firms.start) & (borrowers < lay.energy.stop)
        np.add.at(interest_paid, borrowers[is_prod] - lay.firms.start, due[is_prod])
        self._period["gov_interest"] = int(due[borrowers == gov].sum())
        holders = np.nonzero(L.deposits > 0)[0]
        d_int = _floor_int(L.deposits[holders] * bc["deposit_rate_annual"] / 12)
        L.pay(np.full(holders.size, bank), holders, d_int, "deposit_interest")
        cap_income = np.zeros(H, dtype=np.int64)
        hh_holders = holders < H
        cap_income[holders[hh_holders]] = d_int[hh_holders]

        sched = np.ceil(L.loans[self.producers] / bc["amortization_months"])
        L.repay(self.producers, np.minimum(sched, L.deposits[self.producers]).astype(np.int64))

        # ---- 12 profits, profit tax, dividends
        # Accrual profit: cash flows plus change in the value of inventories
        # (valued at current unit cost, so revaluation is included).
        inv_value = self.inventory * self.unit_cost
        profit = revenue - wage_cost - input_cost - interest_paid
        profit[:F] += inv_value - self.inv_value
        self.inv_value = inv_value
        ptax = np.minimum(self.fiscal.profit_tax(profit), L.deposits[self.producers])
        L.pay(self.producers, np.full(F + E, gov), ptax, "profit_tax")
        self._period["taxes"] += int(ptax.sum())
        # Dividends: producers pay out equity above a target (months of
        # current costs), as far as cash above a liquidity buffer allows.
        costs = wage_cost + input_cost
        months_cash = np.concatenate([np.full(F, fc["cash_buffer_months"]), np.full(E, cfg["energy"]["cash_buffer_months"])])
        months_equity = np.concatenate([np.full(F, fc["equity_target_months"]), np.full(E, cfg["energy"]["equity_target_months"])])
        equity_p = L.deposits[self.producers] - L.loans[self.producers] + np.concatenate([inv_value, np.zeros(E)])
        div = np.minimum(np.maximum(0, equity_p - months_equity * costs),
                         np.maximum(0, L.deposits[self.producers] - months_cash * costs))
        cap_income += self._pay_dividends(self.producers, _floor_int(div), self.owners, "dividends")

        # The bank pays out equity above its target capital ratio on all loans.
        target_equity = bc["capital_target_ratio"] * int(L.loans.sum())
        if L.bank_equity > target_equity:
            b_div = int(L.bank_equity - target_equity)
            cap_income += self._pay_dividends(np.array([bank]), np.array([b_div]), [self.bank_owners], "bank_dividends")

        # ---- 13 insolvency and market entry (goods firms)
        equity = L.deposits[firm_ids] + self.inventory * self.unit_cost - L.loans[firm_ids]
        exits = np.nonzero(equity < 0)[0]
        for j in exits:
            fid = int(firm_ids[j])
            self.employer[self.employer == fid] = -1
            rep = int(min(L.deposits[fid], L.loans[fid]))
            L.repay([fid], [rep], kind="insolvency_repayment")
            L.write_off([fid], [int(L.loans[fid])])
            self.phys.add("goods_written_off", float(self.inventory[j]))
            self.inventory[j] = 0.0
        if exits.size:
            survivors = np.setdiff1d(np.arange(F), exits)
            ref = survivors if survivors.size else np.arange(F)
            w_new = int(self.wage[ref].mean())
            size = max(1.0, float(staff[ref].mean()))
            capital = int(inst["startup_capital_months"] * size * w_new)
            for j in exits:
                # Owners pay in equity in equal shares as far as their deposits
                # allow; any remainder is a start-up loan.
                own = self.owners[j]
                share = np.minimum(capital // own.size, L.deposits[own])
                L.pay(own, np.full(own.size, firm_ids[j]), share, "equity_injection")
                rest = capital - int(share.sum())
                if rest > 0:
                    L.lend([firm_ids[j]], [rest], kind="startup_loan")
            self.inv_value[exits] = 0.0
            self.wage[exits] = w_new
            self.markup[exits] = fc["initial_markup"]
            self.expected_sales[exits] = float(self.expected_sales[ref].mean())
            self.last_sales[exits] = self.expected_sales[exits]
            self.unfilled[exits] = 0
            self.months_all_filled[exits] = 0
            self.cum["firm_exits"] += exits.size

        # ---- 14 government debt management, fiscal memory
        g_out = self._period["benefits"] + self._period["gov_purchases"] + self._period["gov_interest"]
        excess = int(L.deposits[gov]) - max(g_out, 1)
        if excess > 0 and L.loans[gov] > 0:
            L.repay([gov], [min(excess, int(L.loans[gov]))])
        self.fiscal.record(self._period["taxes"], self._period["benefits"], self._period["gov_interest"])
        policy_cost = self._period["transfers"] + self._period["subsidy"] + self._period["investment"]
        self.cum["policy_cost"] += policy_cost

        # ---- 15 checks, household memory, metrics
        L.check_invariants()
        self.phys.check(float(self.inventory.sum()))
        if L.bank_equity < 0:
            self.flags["bank_negative_equity_months"] += 1
        self.capital_income = cap_income
        self.net_income = net_income
        self.income_hist[t % 12] = net_income
        if t < self.policy.start:
            self.quintile = M.quintiles(self.income_hist.mean(axis=0))
        self.e_price_prev = self.e_price.copy()
        self.hh_energy_prev = float(e_kwh.sum())

        rec = M.period_record(
            self, t=t, p_world=p_world, p_hh=p_hh, e_kwh=e_kwh, e_pay=e_pay, forced=forced, need=need,
            net_income=net_income, goods_hh=goods_hh, spend_hh=spend_hh, sold=sold, revenue=revenue,
            e_firms_kwh=float(e_firms_kwh.sum()), imports_kwh=float(e_sales.sum()), exits=exits.size,
            policy_cost=policy_cost,
        )
        self.records.append(rec)
        self.t += 1
        return rec

    def run(self):
        while self.t < self.t_end:
            self.step()
        return self.records

    @property
    def p_ref(self) -> np.ndarray:
        if not hasattr(self, "_p_ref"):
            self._p_ref = self.e_price[self.supplier].copy()
        return self._p_ref

    @p_ref.setter
    def p_ref(self, value: np.ndarray) -> None:
        self._p_ref = value

    def decision_stats(self) -> dict:
        out = {}
        for name in ("household_model", "firm_model", "energy_model", "credit_model"):
            d: Decider = getattr(self, name)
            m = d.model.meta
            out[name] = {"model": m.name, "version": m.version, "kind": m.kind, "calls": d.stats.calls,
                         "agent_decisions": d.stats.agents, "seconds": round(d.stats.seconds, 4),
                         "invalid_actions": d.stats.invalid_actions}
        return out
