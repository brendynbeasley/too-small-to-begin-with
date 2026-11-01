"""Shared inputs for the Baqaee-Farhi decomposition: the firm panel, firm markups, BEA input-output
tables and the San Francisco Fed growth-accounting series.

Imported by src/misallocation.py; not meant to be run on its own.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results"

YEARS = list(range(2011, 2024))   # first full XBRL year to last BEA input-output year
MIN_ASSETS = 10.0                 # $ millions; paper's Appendix C.2 drops firms with assets under $10M
WINSOR = (0.05, 0.95)             # paper winsorizes markups and markup changes at 5-95 by year
DROP_IO = ["GFGD", "GFGN", "GFE", "GSLG", "GSLE", "Used", "Other"]  # government, scrap, noncomparable imports (paper)
ERP_COLUMN = "Implied ERP (FCFE)"  # Damodaran's implied equity risk premium, end of year

# SIC -> BEA summary industry. Most specific prefix wins (4 digits, then 3, then 2). Judgment mapping built
# from the SIC 1987 and NAICS 2017 manuals; financial SICs (60-67) are excluded, as in the paper.
SIC_BEA = {
    "01": "111CA", "02": "111CA", "07": "111CA", "08": "113FF", "09": "113FF",
    "10": "212", "12": "212", "13": "211", "138": "213", "14": "212",
    "15": "23", "16": "23", "17": "23",
    "20": "311FT", "21": "311FT", "22": "313TT", "23": "315AL", "24": "321", "25": "337", "26": "322",
    "27": "323", "271": "511", "272": "511", "273": "511", "274": "511",
    "28": "325", "29": "324", "30": "326", "31": "315AL", "32": "327", "33": "331", "34": "332",
    "35": "333", "357": "334", "36": "335", "365": "334", "366": "334", "367": "334",
    "37": "3364OT", "371": "3361MV", "38": "334", "384": "339", "385": "339", "386": "333", "39": "339",
    "40": "482", "41": "485", "42": "484", "422": "493", "44": "483", "45": "481", "46": "486", "47": "487OS",
    "48": "513", "49": "22", "495": "562",
    "50": "42", "51": "42",
    "52": "4A0", "53": "452", "54": "445", "55": "441", "554": "4A0", "56": "4A0", "57": "4A0", "58": "722",
    "59": "4A0",
    "70": "721", "72": "81", "73": "561", "731": "5412OP", "7370": "514", "7371": "5415", "7372": "511",
    "7373": "5415", "7374": "514", "7377": "532RL", "7379": "5415", "75": "81", "751": "532RL", "76": "81",
    "78": "512", "784": "532RL", "79": "713", "794": "711AS",
    "80": "621", "805": "623", "806": "622", "81": "5411", "82": "61", "83": "624", "84": "711AS",
    "86": "81", "87": "5412OP", "89": "5412OP",
}


def sic_to_bea(sic):
    if pd.isna(sic):
        return None
    s = f"{int(sic):04d}"
    for k in (s, s[:3], s[:2]):
        if k in SIC_BEA:
            return SIC_BEA[k]
    return None


def winsor_by_year(s, years, cut=WINSOR):
    lo = s.groupby(years).transform(lambda x: x.quantile(cut[0]))
    hi = s.groupby(years).transform(lambda x: x.quantile(cut[1]))
    return s.clip(lo, hi)


def user_cost():
    """Real required return r_t = 10-year TIPS yield (annual average) + Damodaran implied ERP."""
    tips = pd.read_csv(RAW / "DFII10.csv")
    tips["year"] = tips.observation_date.str[:4].astype(int)
    tips = tips.set_index("year").DFII10 / 100
    d = pd.read_excel(RAW / "histimpl.xls", header=6)
    d = d[pd.to_numeric(d.Year, errors="coerce").notna()]
    erp = d.set_index(d.Year.astype(int))[ERP_COLUMN].astype(float)
    r = (tips + erp).dropna().rename("r")
    return pd.DataFrame({"tips": tips, "erp": erp, "r": r}).loc[YEARS]


def load_firms(cut=WINSOR, equity_rule=True, drop_losses=False, drop_bea=(), verbose=True):
    """Firm-years after the paper's sample rules, with four markup series.

    The keyword arguments switch individual rules for the robustness table: the winsorizing cut, the
    paper's exclusion of negative book equity, and (not paper rules) dropping loss-making firm-years or
    the firms of some BEA industries, which then take the aggregate markup."""
    f = pd.read_csv(ROOT / "data" / "sec_firm_years.csv")
    n0 = len(f)
    print(f"Loaded {n0} firm-years from data/sec_firm_years.csv ({f.cik.nunique()} filers)")
    f = f[f.year.isin(YEARS)]
    f["bea"] = f.sic.map(sic_to_bea)
    steps = [
        ("no SIC code or non-classifiable", f.bea.notna() | f.sic.between(6000, 6799)),
        ("financial SIC 6000-6799 (paper excludes financials)", ~f.sic.between(6000, 6799)),
        ("no operating income (tag, pretax + interest, or revenue - costs)", f.op_income.notna()),
        ("revenue not positive", f.revenue > 0),
        ("assets missing or under $10M", f.assets >= MIN_ASSETS),
        ("book equity missing or negative (paper rule)", (f.equity > 0) | (not equity_rule)),
        ("operating income at least as large as revenue", f.op_income < f.revenue),
    ]
    for why, keep in steps:
        keep = keep.reindex(f.index)
        if verbose:
            print(f"  dropped {int((~keep).sum()):6d}  {why}")
        f = f[keep]
    r = user_cost()
    f = f.join(r.r, on="year")
    f["ppe_filled"] = f.ppe.isna()
    f["ppe"] = f.ppe.fillna(0)
    tc_ap = f.revenue - f.op_income                       # accounting-profits total cost
    tc_uc = tc_ap + f.r * f.ppe                           # plus a user cost of capital on net PP&E
    f["mu_ap"] = f.revenue / tc_ap
    f["mu_uc"] = f.revenue / tc_uc
    # Cost-share markups (extension): mu = theta x revenue / variable input, theta = industry-year median of
    # that input's share of user-cost total cost. COGS alone (De Loecker-Eeckhout) or all operating costs
    # (Traina's COGS + SG&A, which in filings is everything above the operating-income line).
    ok = (f.cogs > 0) & (f.cogs < tc_uc)
    f["cogs_share"] = np.where(ok, f.cogs / tc_uc, np.nan)
    f["opex_share"] = np.where(ok, tc_ap / tc_uc, np.nan)
    th_c = f.groupby(["bea", "year"]).cogs_share.transform("median")
    th_o = f.groupby(["bea", "year"]).opex_share.transform("median")
    f["mu_cogs"] = np.where(ok, th_c * f.revenue / f.cogs, np.nan)
    f["mu_opex"] = np.where(ok, th_o * f.revenue / tc_ap, np.nan)
    f["mu_uc_raw"] = f.mu_uc        # before winsorizing, for the worked examples
    if drop_losses:
        f = f[f.op_income > 0].copy()
    f = f[~f.bea.isin(drop_bea)].copy()
    for m in ["mu_ap", "mu_uc", "mu_cogs", "mu_opex"]:
        f[m] = winsor_by_year(f[m], f.year, cut)
    if not verbose:
        return f
    print(f"Kept {len(f)} firm-years ({f.cik.nunique()} firms) in {f.bea.nunique()} BEA industries; "
          f"{int(f.ppe_filled.sum())} firm-years have no net PP&E tag (user cost set to zero)")
    print(f"  {int(ok.sum())} firm-years also report COGS (used for the cost-share markups)")
    return f


def load_io():
    """BEA summary use tables, before redefinitions, producers' prices: one dict per year."""
    path = RAW / "IOUse_Before_Redefinitions_PRO_1997-2023_Summary.xlsx"
    io = {}
    for y in YEARS:
        d = pd.read_excel(path, sheet_name=str(y), header=None)
        codes = d.iloc[5, 2:].tolist()
        rows = d.iloc[7:, 0].tolist()
        vals = d.iloc[7:, 2:].apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy()
        t = pd.DataFrame(vals, index=rows, columns=codes)
        names = dict(zip(d.iloc[7:78, 0], d.iloc[7:78, 1]))
        ind = [c for c in d.iloc[7:78, 0] if c not in DROP_IO]
        go = d.iloc[7:, :][d.iloc[7:, 1] == "Total Industry Output"].iloc[0, 2:]
        go = pd.Series(pd.to_numeric(go.values, errors="coerce"), index=codes)[ind]
        tot_int = d.iloc[7:, :][d.iloc[7:, 1] == "Total Intermediate"].iloc[0, 2:]
        tot_int = pd.Series(pd.to_numeric(tot_int.values, errors="coerce"), index=codes)[ind]
        comp = t.loc["V001", ind]
        use = t.loc[ind, ind]                              # commodity (row) used by industry (column)
        va = go - tot_int
        gdp = va.sum()
        io[y] = {
            "ind": ind, "names": names,
            "Omega": (use / go).T.to_numpy(),               # Omega[I, J] = spending of I on J / sales of I
            "lam": (go / gdp).to_numpy(),                   # revenue-based Domar weights
            "comp_share": (comp / go).to_numpy(),           # Omega[I, L]
            "gos_share": ((va - comp) / go).to_numpy(),     # paper: GOS = sales - intermediates - compensation
            "go": go, "gdp": gdp,
        }
    print(f"Loaded BEA use tables {YEARS[0]}-{YEARS[-1]}: {len(io[YEARS[0]]['ind'])} industries after dropping "
          f"{', '.join(DROP_IO)}")
    return io


def load_tfp():
    """Fernald (SF Fed) annual business-sector growth accounting, log points (x100 in the file)."""
    d = pd.read_excel(RAW / "quarterly_tfp.xlsx", sheet_name="annual")
    d = d[pd.to_numeric(d.date, errors="coerce").notna()].copy()
    d["year"] = d.date.astype(int)
    d = d.set_index("year")[["dY", "dhours", "dLQ", "dk", "alpha", "dtfp"]].astype(float)
    d[["dY", "dhours", "dLQ", "dk", "dtfp"]] /= 100
    d["dL"] = d.dhours + d.dLQ
    return d
