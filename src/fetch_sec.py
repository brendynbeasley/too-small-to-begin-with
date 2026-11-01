"""Build the firm-year panel of US public companies from SEC 10-K filings.

Baqaee and Farhi (2020) take firm sales and markups from Compustat, which is licensed. The free
substitute is the SEC's Financial Statement Data Sets: every quarter the SEC publishes all the XBRL
numbers filed that quarter (num.txt) with the filer's SIC code (sub.txt). This script reads the
10-K filings in the 55 quarterly files 2012q1-2025q3 and keeps, for each company and fiscal year,
revenue, operating income, cost of goods sold, SG&A, R&D, net property plant and equipment, total
assets and book equity. Fiscal years follow the Compustat convention (a year ending January-May
belongs to the previous fiscal year). Fiscal 2011 comes partly from the prior-year comparatives in
fiscal 2012 10-Ks, because the files read here start in 2012q1 (the first full year of XBRL filing by all
companies is fiscal 2011).

Output: data/sec_firm_years.csv (one row per firm-year, $ millions, committed so the analysis runs
offline). The quarterly zips (about 5 GB) are downloaded to data/raw/sec/ and ignored by git.

Usage:
    python src/fetch_sec.py
"""

import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SEC_DIR = ROOT / "data" / "raw" / "sec"
OUT_FILE = ROOT / "data" / "sec_firm_years.csv"

YEARS = list(range(2011, 2024))   # 2011: first year all filers tagged XBRL; 2023: last BEA input-output year
QUARTERS = [f"{y}q{q}" for y in range(2012, 2026) for q in range(1, 5) if f"{y}q{q}" <= "2025q3"]
HEADERS = {"User-Agent": "Brendyn Beasley research 83249437+brendynbeasley@users.noreply.github.com",
           "Accept-Encoding": "gzip, deflate"}
PAUSE = 1.0                       # seconds between SEC downloads

# Revenue: the largest of the tags a filer reports for the year (each is a candidate for total revenue).
REVENUE_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet"]
COGS_TAGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"]  # first available, in this order
FLOW = {"SellingGeneralAndAdministrativeExpense": "sga", "ResearchAndDevelopmentExpense": "rnd"}
STOCK = {"Assets": "assets", "StockholdersEquity": "equity"}
# Operating income: the tag if reported; otherwise pretax income plus interest expense; otherwise revenue
# minus total costs and expenses (filers such as ExxonMobil and Chevron report no operating-income line).
OPINC = "OperatingIncomeLoss"
PRETAX = ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
          "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]
OTHER_FLOW = [OPINC, "InterestExpense", "CostsAndExpenses"] + PRETAX
PPE_TAGS = ["PropertyPlantAndEquipmentNet",   # net PP&E, then the version that includes finance-lease assets
            "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"]
FLOW_TAGS = REVENUE_TAGS + COGS_TAGS + list(FLOW) + OTHER_FLOW
ALL_TAGS = set(FLOW_TAGS) | set(STOCK) | set(PPE_TAGS)


def fiscal_year(dates):
    """Compustat convention: fiscal years ending January to May belong to the previous year."""
    d = pd.to_datetime(dates.astype(int).astype(str), format="%Y%m%d")
    return np.where(d.dt.month >= 6, d.dt.year, d.dt.year - 1)


def get_zip(q):
    path = SEC_DIR / f"fsds_{q}.zip"
    if not path.exists():
        time.sleep(PAUSE)
        url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{q}.zip"
        print(f"  downloading {url}")
        r = requests.get(url, headers=HEADERS, timeout=1200)
        if r.status_code != 200:
            raise SystemExit(f"SEC returned {r.status_code} for {url}")
        tmp = path.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.rename(path)
    return path


def read_quarter(q):
    """10-K facts for our tags from one quarterly file: current year and the prior-year comparative."""
    with zipfile.ZipFile(get_zip(q)) as z:
        sub = pd.read_csv(z.open("sub.txt"), sep="\t", dtype=str,
                          usecols=["adsh", "cik", "name", "sic", "form", "period", "filed"])
        sub = sub[sub.form == "10-K"].dropna(subset=["period"])
        keep = set(sub.adsh)
        parts = []
        reader = pd.read_csv(z.open("num.txt"), sep="\t", dtype=str, chunksize=2_000_000,
                             encoding="latin-1", on_bad_lines="skip")
        for c in reader:
            c = c[c.adsh.isin(keep) & c.tag.isin(ALL_TAGS) & (c.uom == "USD")
                  & c.version.str.startswith("us-gaap", na=False) & c.coreg.isna()]
            if "segments" in c:
                c = c[c.segments.isna()]
            parts.append(c[["adsh", "tag", "ddate", "qtrs", "value"]])
    n = pd.concat(parts)
    n = n.merge(sub, on="adsh")
    n["value"] = pd.to_numeric(n.value, errors="coerce")
    n["qtrs"] = n.qtrs.astype(int)
    n = n[(n.tag.isin(FLOW_TAGS) & (n.qtrs == 4)) | (n.tag.isin(list(STOCK) + PPE_TAGS) & (n.qtrs == 0))]
    n["fyear"] = fiscal_year(n.ddate)
    n["filing_fyear"] = fiscal_year(n.period)
    n["lag"] = n.filing_fyear - n.fyear
    n = n[n.lag.isin([0, 1])]
    return n[["cik", "name", "sic", "tag", "fyear", "lag", "filed", "value"]]


def main():
    SEC_DIR.mkdir(parents=True, exist_ok=True)
    facts = []
    for q in QUARTERS:
        t0 = time.time()
        d = read_quarter(q)
        facts.append(d)
        print(f"{q}: {d.cik.nunique()} 10-K filers, {len(d)} facts ({time.time() - t0:.0f}s)")
    f = pd.concat(facts)
    f = f[f.fyear.isin(YEARS)]
    # Prefer the year's own 10-K (lag 0) over the next year's comparative (lag 1); latest filing first.
    f = f.sort_values(["cik", "fyear", "tag", "lag", "filed"], ascending=[True, True, True, True, False])
    f = f.drop_duplicates(["cik", "fyear", "tag"])
    wide = f.pivot_table(index=["cik", "fyear"], columns="tag", values="value", aggfunc="first")
    wide = wide.reindex(columns=sorted(ALL_TAGS))
    out = pd.DataFrame(index=wide.index)
    out["revenue"] = wide[REVENUE_TAGS].max(axis=1)
    out["cogs"] = np.nan
    for t in COGS_TAGS:
        out["cogs"] = out.cogs.fillna(wide[t])
    for t, k in {**FLOW, **STOCK}.items():
        out[k] = wide[t]
    out["ppe"] = wide[PPE_TAGS[0]].fillna(wide[PPE_TAGS[1]])
    pretax = wide[PRETAX[0]].fillna(wide[PRETAX[1]]) + wide.InterestExpense.fillna(0)
    by_costs = out.revenue - wide.CostsAndExpenses
    out["op_income"] = wide[OPINC].fillna(pretax).fillna(by_costs)
    out["op_source"] = np.select([wide[OPINC].notna(), pretax.notna(), by_costs.notna()],
                                 ["tag", "pretax+interest", "revenue-costs"], "none")
    money = ["revenue", "cogs", "sga", "rnd", "assets", "equity", "ppe", "op_income"]
    out = out.dropna(subset=["revenue"])
    out[money] = out[money] / 1e6                   # dollars -> $ millions
    info = (f.sort_values("filed").groupby("cik")[["name", "sic"]].last())
    out = out.reset_index().rename(columns={"fyear": "year"}).join(info, on="cik")
    out = out.rename(columns={"name": "entity"})
    out["sic"] = pd.to_numeric(out.sic, errors="coerce").astype("Int64")
    cols = ["cik", "entity", "sic", "year", "revenue", "op_income", "cogs", "sga", "rnd", "assets", "ppe", "equity", "op_source"]
    out = out[cols].sort_values(["cik", "year"])
    for y, g in out.groupby("year"):
        print(f"FY{y}: {len(g)} firms report revenue; {g.op_income.notna().sum()} have operating income")
    out.round(4).to_csv(OUT_FILE, index=False)
    print(f"Wrote {len(out)} firm-years for {out.cik.nunique()} companies to {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
