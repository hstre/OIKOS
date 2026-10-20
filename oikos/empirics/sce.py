"""Data preparation for the empirical test with the NY Fed Survey of
Consumer Expectations (SCE).

Source: Survey of Consumer Expectations, © 2013-2026 Federal Reserve Bank of
New York (FRBNY). The SCE data are available without charge at
www.newyorkfed.org and may be used subject to license terms posted there.
FRBNY disclaims any responsibility or legal liability for this analysis and
interpretation of Survey of Consumer Expectations data. The data prepared
here are modified (selected variables, recoded, one record per respondent).

Raw files are downloaded on demand, verified against pinned SHA-256 hashes
and never committed. Everything that defines the analysis sample and the
split is deterministic and fixed in configs/experiments/sce_validation.yaml.
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://www.newyorkfed.org"
SOURCES = {
    "sce-household-spending-microdata.xlsx": (
        "/medialibrary/media/research/microeconomics/interactive/downloads/sce-household-spending-microdata.xlsx",
        "28a7db5ab148914c03e5a54883f583ce628ed1ee178f188f29c2c70a0f615ad2"),
    "frbny-sce-public-microdata-complete-13-16.xlsx": (
        "/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-public-microdata-complete-13-16.xlsx",
        "4107965060e133a9e2d8c672a97eec2e11e3c2768c649a68a71ee6db966ea05a"),
    "frbny-sce-public-microdata-complete-17-19.xlsx": (
        "/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-public-microdata-complete-17-19.xlsx",
        "a88e5a225c9a566dd8cdfdd77abef9ac456eb52d1a120c5ec208184a88c745c9"),
    "frbny-sce-public-microdata-20-24.xlsx": (
        "/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-public-microdata-20-24.xlsx",
        "1b57ffb75c2170d767f46a001002db8c40c228fe5691f6dd19e39777ffe469c6"),
}

# Outcome: QSP13new "Now imagine that next year you were to find yourself with 10% less
# household income. What would you do?" (answer codes 1-7, wording from the SCE questionnaire)
OUTCOME_LABELS_7 = {
    1: "Cut spending by the whole amount",
    2: "Not cut spending at all, but cut my savings by the whole amount",
    3: "Not cut spending at all, but increase my debt by borrowing the whole amount",
    4: "Cut spending by some and cut savings by some",
    5: "Cut spending by some and increase debt by some",
    6: "Cut savings by some and increase debt by some",
    7: "Cut spending by some, cut savings by some and increase debt some",
}
# Primary outcome: does the household cut spending, and by how much of the loss?
COLLAPSE_3 = {1: 0, 4: 1, 5: 1, 7: 1, 2: 2, 3: 2, 6: 2}
OUTCOME_LABELS_3 = ["full_cut", "partial_cut", "no_cut"]

EMPLOYMENT_ORDER = [  # first matching code wins (Q10 is multi-select)
    (1, "working full-time"), (2, "working part-time"), (4, "temporarily laid off"),
    (5, "on sick or other leave"), (3, "not working, but would like to work"),
    (7, "retired"), (8, "student"), (9, "homemaker"), (6, "permanently disabled"), (10, "other"),
]

SPENDING_COLS = ["userid", "date", "qsp13new"]
CORE_COLS = (["date", "userid", "weight"] + [f"Q10_{i}" for i in range(1, 11)]
             + ["Q13new", "Q25v2", "Q25v2part2", "Q26v2", "Q26v2part2", "Q30new",
                "_AGE_CAT", "_EDU_CAT", "_HH_INC_CAT"])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(raw_dir: str | Path, log=print) -> None:
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    for name, (path, digest) in SOURCES.items():
        target = raw / name
        if not target.exists():
            log(f"downloading {name}")
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0 (OIKOS research)"})
            with urllib.request.urlopen(req, timeout=600) as r, open(target, "wb") as f:
                f.write(r.read())
        got = sha256(target)
        if got != digest:
            raise ValueError(f"{name}: SHA-256 {got} differs from the pinned {digest}; the source file has "
                             "changed. Do not silently continue: review and re-register the data version.")


def employment(row: pd.Series) -> str:
    for code, label in EMPLOYMENT_ORDER:
        if row.get(f"Q10_{code}") == 1:
            return label
    return "unknown"


def _signed(direction, magnitude):
    if pd.isna(direction) or pd.isna(magnitude):
        return np.nan
    return float(magnitude) if direction == 1 else -float(magnitude)


def build(raw_dir: str | Path) -> pd.DataFrame:
    """One record per respondent: the first spending-module wave with a valid
    QSP13new answer, joined with the core survey of the same month."""
    raw = Path(raw_dir)
    sp = pd.read_excel(raw / "sce-household-spending-microdata.xlsx", header=1, usecols=SPENDING_COLS)
    first_any = sp.groupby("userid").date.min().rename("first_spending_date")
    sp = sp[sp.qsp13new.isin(OUTCOME_LABELS_7)]
    core = pd.concat([pd.read_excel(raw / f, header=1, usecols=lambda c: c in CORE_COLS)
                      for f in SOURCES if f.startswith("frbny-sce-public")], ignore_index=True)
    df = sp.merge(core, on=["userid", "date"], how="inner", validate="one_to_one")
    df = df.sort_values(["userid", "date"]).groupby("userid", as_index=False).first()
    df = df.merge(first_any, on="userid")
    out = pd.DataFrame({
        "userid": df.userid.astype(int),
        "date": df.date.astype(int),
        "first_spending_date": df.first_spending_date.astype(int),
        "weight": df.weight,
        "age_group": df._AGE_CAT,
        "education": df._EDU_CAT,
        "household_income_group": df._HH_INC_CAT,
        "employment": df.apply(employment, axis=1),
        "job_loss_chance_12m": df.Q13new,
        "expected_income_change_12m": [_signed(a, b) for a, b in zip(df.Q25v2, df.Q25v2part2)],
        "expected_spending_change_12m": [_signed(a, b) for a, b in zip(df.Q26v2, df.Q26v2part2)],
        "debt_payment_miss_chance_3m": df.Q30new,
        "y7": df.qsp13new.astype(int),
    })
    out["y3"] = out.y7.map(COLLAPSE_3).astype(int)
    return out


def assign(df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Deterministic, pre-registered split and presentation assignment."""
    s = spec["split"]
    key = s["hash_salt"]
    h = df.userid.map(lambda u: int(hashlib.sha256(f"{key}:{u}".encode()).hexdigest()[:12], 16))
    df = df.assign(hash=h)
    period = np.where(df.first_spending_date < s["train_before"], "train",
                      np.where(df.first_spending_date >= s["test_from"], "test", "excluded_gap"))
    df["period"] = period
    df["set"] = df.period
    adj_pool = df[(df.period == "train") & (df.date >= s["adjustment_from"])].sort_values("hash")
    df.loc[adj_pool.index[: s["adjustment_n"]], "set"] = "adjustment"
    test_pool = df[df.period == "test"].sort_values("hash")
    df.loc[df.period == "test", "set"] = "test_unused"
    df.loc[test_pool.index[: s["test_n"]], "set"] = "test"
    ctrl_pool = df[df.set == "adjustment"].sort_values("hash")
    df["technical_control"] = False
    df.loc[ctrl_pool.index[: spec["technical_control"]["n"]], "technical_control"] = True
    df["presentation"] = (df.hash % len(spec["presentations"]["orders"])).astype(int)
    return df


def check_no_leakage(df: pd.DataFrame) -> None:
    train_ids = set(df.loc[df.period == "train", "userid"])
    test_ids = set(df.loc[df.period == "test", "userid"])
    if train_ids & test_ids:
        raise AssertionError("respondents in both training and test period")
    if df.userid.duplicated().any():
        raise AssertionError("more than one record per respondent")
