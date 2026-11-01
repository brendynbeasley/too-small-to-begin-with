"""Baqaee and Farhi (2020) on 2011-2023 US data: how much of TFP growth came from reallocation?

Implements equation (7) of Baqaee and Farhi, "Productivity and Misallocation in General Equilibrium"
(QJE 2020), the way their Section 7.2 does: firm markups from company filings, an input-output
network from the BEA summary use tables, firms assigned to BEA industries, and the cumulated
change in allocative efficiency

    dAE_t = - sum_i lt_i,t-1 dlog mu_i,t  -  sum_f Lt_f,t-1 dlog Lambda_f,t

compared with the cumulated distortion-adjusted Solow residual dlog Y - sum_f Lt_f dlog L_f. Here
lt are cost-based Domar weights, Lt cost-based factor shares and Lambda factor income shares
(labor and capital). Each step t-1 -> t uses the firms present in both years.

Outputs (results/):
    decomposition.csv          year-by-year TFP, allocative efficiency and technology, every markup series
    summary.csv                cumulated totals and shares, with bootstrap intervals
    markup_between_within.csv  paper's Figure 3: aggregate markup change split into within and between firms
    share_regression.csv       do sales shares grow faster at high-markup firms? (the mechanism)
    contributors.csv           firms behind the within-industry reallocation term
    industries.csv             BEA industries: firms, markups, cost-based Domar weights
    cumulative.png, markup_between_within.png

Usage:
    python src/fetch_sec.py        # once, needs internet (data/sec_firm_years.csv is committed)
    python src/misallocation.py
"""

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so python -I finds inputs.py
import inputs as I  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)
SERIES = {"mu_uc": "User cost (paper's benchmark)", "mu_ap": "Accounting profits",
          "mu_cogs": "COGS cost share (De Loecker-Eeckhout style)", "mu_opex": "All operating costs, cost share (Traina style)"}
BOOT_REPS = 200        # firm-level bootstrap draws for the cumulated totals
SEED = 20200101
NAMES = {320193: "Apple", 789019: "Microsoft", 1652044: "Alphabet", 1326801: "Meta", 1045810: "Nvidia",
         1018724: "Amazon", 104169: "Walmart", 909832: "Costco", 64803: "CVS Health", 1318605: "Tesla",
         1467858: "General Motors", 78003: "Pfizer", 1682852: "Moderna", 1163165: "ConocoPhillips"}
ENERGY = ("211", "213", "324")  # oil and gas extraction, mining support, petroleum refining (BEA summary codes)
MIN_FIRMS = 3          # judgment: an industry's markup comes from its filers only if there are 3 or more ...
MIN_COVERAGE = 0.01    # ... whose revenue is at least 1% of BEA gross output; otherwise the aggregate markup


def network(io_y, mu_ind):
    """Cost-based Domar weights and factor shares for one year, given industry markups (paper Sec. 7.1)."""
    Om, lam, mu = io_y["Omega"], io_y["lam"], mu_ind
    om_L = io_y["comp_share"]
    om_K = np.maximum(io_y["gos_share"] - (1 - 1 / mu), 0)       # capital = GOS minus profits, floored at 0
    Lam = np.array([lam @ om_L, lam @ om_K])                     # factor income shares of GDP
    b = np.maximum(lam - lam @ Om, 0)                            # final-demand shares
    b = b / b.sum()
    Om_t = mu[:, None] * Om                                      # cost-based input-output matrix
    lt = np.linalg.solve((np.eye(len(b)) - Om_t).T, b)           # lt' = b'(I - Om_t)^-1
    Lt = np.array([lt @ (mu * om_L), lt @ (mu * om_K)])
    return lt, Lt / Lt.sum(), Lam


def covered(g, io_y):
    """Industries where public filers are numerous enough to stand for the industry."""
    x = g.groupby("bea").revenue.agg(["sum", "size"])
    share = x["sum"] / io_y["go"].reindex(x.index)
    return set(x.index[(x["size"] >= MIN_FIRMS) & (share >= MIN_COVERAGE)])


def industry_markups(g, ind, col, cov):
    """Harmonic sales-weighted industry markups (paper Sec. 7.1); uncovered industries get the aggregate one."""
    inv = (g.s * (1 / g[col])).groupby(g.bea).sum()
    agg = 1 / ((g.rev_w * (1 / g[col])).sum() / g.rev_w.sum())
    return np.array([1 / inv[i] if i in cov else agg for i in ind]), agg


def step(prev, cur, io0, io1, col, cut):
    """One year of the decomposition among firms present in both years."""
    both = prev.index.intersection(cur.index)
    p, c = prev.loc[both].copy(), cur.loc[both].copy()
    for g in (p, c):
        g["rev_w"] = g.revenue
        g["s"] = g.revenue / g.groupby("bea").revenue.transform("sum")
    ind = io0["ind"]
    cov = covered(p, io0) & covered(c, io1)
    mu0, agg0 = industry_markups(p, ind, col, cov)
    mu1, agg1 = industry_markups(c, ind, col, cov)
    lt0, Lt0, Lam0 = network(io0, mu0)
    _, _, Lam1 = network(io1, mu1)
    pos = {k: n for n, k in enumerate(ind)}
    p, c = p[p.bea.isin(cov)], c[c.bea.isin(cov)]           # firm detail only where the industry is covered
    lt_firm = p.s * p.bea.map(lambda k: lt0[pos[k]])
    dlogmu = np.log(c[col] / p[col])
    dlogmu = I.winsor_by_year(dlogmu, pd.Series(0, index=dlogmu.index), cut)
    uncov = np.array([i not in cov for i in ind])
    markup_term = -(lt_firm * dlogmu).sum() - (lt0[uncov] @ np.log(mu1[uncov] / mu0[uncov]))
    factor_term = -(Lt0 @ np.log(Lam1 / Lam0))
    ae_firm = markup_term + factor_term
    ae_ind = -(lt0 @ np.log(mu1 / mu0)) + factor_term
    # within-industry reallocation piece of (firm - industry): lt_I * mu_I * ds_i * Lerner_i
    k = p.bea.map(pos)
    contrib = lt0[k] * mu0[k] * (c.s - p.s) * (1 - 1 / p[col])
    out = {"ae_firm": ae_firm, "ae_industry": ae_ind, "factor_term": factor_term,
           "markup_term": markup_term, "Lt_labor": Lt0[0], "Lt_capital": Lt0[1],
           "Lambda_labor": Lam0[0], "Lambda_capital": Lam0[1], "agg_markup": agg0,
           "domar_sum": lt0.sum(), "firms": len(both), "covered_industries": len(cov)}
    return out, contrib.rename("contrib")


def decompose(f, io, tfp, col, cut=I.WINSOR):
    rows, contribs = [], []
    panel = {y: f[f.year == y].set_index("cik") for y in I.YEARS}
    for y in I.YEARS[1:]:
        p, c = panel[y - 1].dropna(subset=[col]), panel[y].dropna(subset=[col])
        out, con = step(p, c, io[y - 1], io[y], col, cut)
        t = tfp.loc[y]
        out["year"] = y
        out["tfp_adjusted"] = t.dY - out["Lt_labor"] * t.dL - out["Lt_capital"] * t.dk
        out["tfp_fernald"] = t.dtfp
        rows.append(out)
        contribs.append(con.to_frame().assign(year=y))
    d = pd.DataFrame(rows).set_index("year")
    d["technology"] = d.tfp_adjusted - d.ae_firm
    return d, pd.concat(contribs)


def summarize(d):
    cum = d[["tfp_adjusted", "tfp_fernald", "ae_firm", "ae_industry", "technology"]].sum()
    return {"cum_tfp_adjusted": cum.tfp_adjusted, "cum_tfp_fernald": cum.tfp_fernald,
            "cum_ae_firm": cum.ae_firm, "cum_ae_industry": cum.ae_industry, "cum_technology": cum.technology,
            "share_ae_of_tfp": cum.ae_firm / cum.tfp_adjusted,
            "share_ae_industry_of_tfp": cum.ae_industry / cum.tfp_adjusted}


def bootstrap(f, io, tfp, col, reps):
    """Resample firms with replacement (each draw keeps a firm's whole history)."""
    rng = np.random.default_rng(SEED)
    firms = f.cik.unique()
    by_firm = {k: g for k, g in f.groupby("cik")}
    draws = []
    for r in range(reps):
        pick = rng.choice(firms, size=len(firms), replace=True)
        b = pd.concat([by_firm[k].assign(cik=n) for n, k in enumerate(pick)])
        d, con = decompose(b, io, tfp, col)
        s = summarize(d)
        s["within_realloc"] = con.contrib.sum()
        draws.append(s)
    return pd.DataFrame(draws)


def between_within(f, col):
    """Paper's Figure 3 (footnote 43): change in the harmonic sales-weighted markup, within vs between."""
    rows = []
    panel = {y: f[f.year == y].set_index("cik") for y in I.YEARS}
    for y in I.YEARS[1:]:
        both = panel[y - 1].index.intersection(panel[y].index)
        p, c = panel[y - 1].loc[both], panel[y].loc[both]
        w0, w1 = p.revenue / p.revenue.sum(), c.revenue / c.revenue.sum()
        m0 = 1 / (w0 / p[col]).sum()
        m1 = 1 / (w1 / c[col]).sum()
        dlog = np.log(m1 / m0)
        within = ((w0 / p[col]) * np.log(c[col] / p[col])).sum() / (w0 / p[col]).sum()
        rows.append({"year": y, "dlog_markup": dlog, "within": within, "between": dlog - within,
                     "markup_start": m0})
    d = pd.DataFrame(rows).set_index("year")
    for k in ["dlog_markup", "within", "between"]:
        d["cum_" + k] = d[k].cumsum()
    return d


def share_regression(f, col):
    """dlog s_i,t = a_(industry x year) + b * Lerner_i,t-1 + e; null b = 0. SEs clustered by firm."""
    g = f.sort_values(["cik", "year"]).copy()
    g["s"] = g.revenue / g.groupby(["bea", "year"]).revenue.transform("sum")
    g["lerner"] = 1 - 1 / g[col]
    g["s_lag"] = g.groupby("cik").s.shift()
    g["lerner_lag"] = g.groupby("cik").lerner.shift()
    g["bea_lag"] = g.groupby("cik").bea.shift()
    g["gap"] = g.year - g.groupby("cik").year.shift()
    g = g[(g.gap == 1) & (g.bea == g.bea_lag) & (g.s_lag > 0) & (g.s > 0)].dropna(subset=["lerner_lag"])
    g["dlog_s"] = np.log(g.s / g.s_lag)
    g["dlog_s"] = I.winsor_by_year(g.dlog_s, g.year)
    g["cell"] = g.bea + "_" + g.year.astype(str)
    rows = []
    for name, w in [("equal-weighted", None), ("sales-weighted", g.s_lag)]:
        mod = smf.wls("dlog_s ~ lerner_lag + C(cell)", data=g, weights=w if w is not None else 1.0)
        res = mod.fit(cov_type="cluster", cov_kwds={"groups": g.cik})
        b, se = res.params.lerner_lag, res.bse.lerner_lag
        rows.append({"weights": name, "beta": b, "se": se, "ci_low": b - 1.96 * se, "ci_high": b + 1.96 * se,
                     "p": res.pvalues.lerner_lag, "n": int(res.nobs), "firms": g.cik.nunique(),
                     "cells": g.cell.nunique()})
    return pd.DataFrame(rows)


def main():
    I.OUT.mkdir(exist_ok=True)
    f = I.load_firms()
    io = I.load_io()
    tfp = I.load_tfp()

    decs, sums, contribs = [], [], {}
    for col, label in SERIES.items():
        sample = f.dropna(subset=["mu_cogs"]) if col in ("mu_cogs", "mu_opex") else f
        d, con = decompose(sample, io, tfp, col)
        decs.append(d.assign(series=col))
        contribs[col] = con
        s = summarize(d)
        s.update(series=col, label=label, firm_years=len(sample), firms=sample.cik.nunique(),
                 within_realloc=con.contrib.sum())
        sums.append(s)
        print(f"{label}: cumulated AE {s['cum_ae_firm']:+.4f}, adjusted TFP {s['cum_tfp_adjusted']:+.4f}, "
              f"share {s['share_ae_of_tfp']:.2f}; industry-level AE {s['cum_ae_industry']:+.4f}")
    # Same-sample check: the paper's two total-cost series on the firms that report COGS
    for col in ("mu_uc", "mu_ap"):
        d, con = decompose(f.dropna(subset=["mu_cogs"]), io, tfp, col)
        s = summarize(d)
        s.update(series=col + "_cogs_sample", label=SERIES[col] + ", COGS reporters only",
                 within_realloc=con.contrib.sum(),
                 firm_years=int(f.mu_cogs.notna().sum()), firms=f.dropna(subset=["mu_cogs"]).cik.nunique())
        sums.append(s)
        print(f"{s['label']}: cumulated AE {s['cum_ae_firm']:+.4f}, share {s['share_ae_of_tfp']:.2f}")
    dec = pd.concat(decs)
    dec.round(6).to_csv(I.OUT / "decomposition.csv")
    summ = pd.DataFrame(sums).set_index("series")

    print(f"Bootstrap ({BOOT_REPS} firm resamples) for the user-cost and accounting-profit series ...")
    for col in ("mu_uc", "mu_ap"):
        bs = bootstrap(f, io, tfp, col, BOOT_REPS)
        for k in ["cum_ae_firm", "cum_ae_industry", "share_ae_of_tfp", "within_realloc"]:
            summ.loc[col, k + "_lo"] = bs[k].quantile(0.025)
            summ.loc[col, k + "_hi"] = bs[k].quantile(0.975)
    summ.round(5).to_csv(I.OUT / "summary.csv")

    # Robustness: one rule changed at a time, user-cost markups
    rob = []
    variants = [("Paper's rules (benchmark)", {}),
                ("Winsorize at 1-99 instead of 5-95", {"cut": (0.01, 0.99)}),
                ("Keep negative-equity firms", {"equity_rule": False}),
                ("Drop loss-making firm-years", {"drop_losses": True}),
                ("Oil, gas and refining take the aggregate markup", {"drop_bea": ENERGY})]
    for name, kw in variants:
        g = I.load_firms(verbose=False, **kw)
        d, con = decompose(g, io, tfp, "mu_uc", kw.get("cut", I.WINSOR))
        s = summarize(d)
        s.update(variant=name, firm_years=len(g), within_realloc=con.contrib.sum(),
                 cum_between=between_within(g, "mu_uc").cum_between.iloc[-1])
        rob.append(s)
        print(f"  {name}: AE {s['cum_ae_firm']:+.4f}, industry AE {s['cum_ae_industry']:+.4f}, "
              f"within-industry reallocation {s['within_realloc']:+.4f}")
    pd.DataFrame(rob).set_index("variant").round(5).to_csv(I.OUT / "robustness.csv")

    bw = between_within(f, "mu_uc")
    bw.round(6).to_csv(I.OUT / "markup_between_within.csv")
    print(f"Aggregate user-cost markup {bw.markup_start.iloc[0]:.3f} in {I.YEARS[0]}; cumulated change "
          f"{bw.cum_dlog_markup.iloc[-1]:+.4f} (within {bw.cum_within.iloc[-1]:+.4f}, "
          f"between {bw.cum_between.iloc[-1]:+.4f})")

    reg = pd.concat([share_regression(f, c).assign(series=c) for c in SERIES])
    reg.round(6).to_csv(I.OUT / "share_regression.csv", index=False)
    print(reg[["series", "weights", "beta", "se", "p", "n"]].to_string(index=False))

    # Who drove the within-industry reallocation (user-cost markups)
    con = contribs["mu_uc"].reset_index()
    info = f.groupby("cik").agg(entity=("entity", "last"), bea=("bea", "last"))
    first = f[f.year == I.YEARS[0]].set_index("cik")
    last = f[f.year == I.YEARS[-1]].set_index("cik")
    tot = con.groupby("cik").contrib.sum().to_frame().join(info)
    tot["markup_mean"] = f.groupby("cik").mu_uc.mean()
    tot["revenue_first"] = first.revenue
    tot["revenue_last"] = last.revenue
    tot["markup_first"] = first.mu_uc
    tot["markup_last"] = last.mu_uc
    tot["years"] = con.groupby("cik").size()
    tot = tot.sort_values("contrib", ascending=False)
    tot.round(6).to_csv(I.OUT / "contributors.csv")
    print(f"Within-industry reallocation summed over firms: {tot.contrib.sum():+.4f}")

    # Names table: well-known firms, first and last year, raw inputs and markups
    g = f.copy()
    g["s"] = g.revenue / g.groupby(["bea", "year"]).revenue.transform("sum")
    rows = []
    for cik, short in NAMES.items():
        x = g[g.cik == cik].sort_values("year")
        if x.empty:
            continue
        a, z = x.iloc[0], x.iloc[-1]
        rows.append({"cik": cik, "name": short, "bea": z.bea, "first_year": a.year, "last_year": z.year,
                     "revenue_first": a.revenue, "revenue_last": z.revenue, "op_income_last": z.op_income,
                     "ppe_last": z.ppe, "r_last": z.r, "user_cost_last": z.r * z.ppe,
                     "markup_raw_last": z.mu_uc_raw, "lerner_raw_last": 1 - 1 / z.mu_uc_raw, "markup_last": z.mu_uc,
                     "markup_first": a.mu_uc, "share_first": a.s, "share_last": z.s,
                     "contrib": tot.contrib.get(cik, np.nan)})
    pd.DataFrame(rows).round(5).to_csv(I.OUT / "names.csv", index=False)

    # Industry table
    y0, y1 = I.YEARS[0], I.YEARS[-1]
    rows = []
    for y in I.YEARS:
        g = f[f.year == y].copy()
        g["s"] = g.revenue / g.groupby("bea").revenue.transform("sum")
        g["rev_w"] = g.revenue
        cov = covered(g, io[y])
        mu, agg = industry_markups(g, io[y]["ind"], "mu_uc", cov)
        lt, _, _ = network(io[y], mu)
        for n, k in enumerate(io[y]["ind"]):
            gi = g[g.bea == k]
            rows.append({"year": y, "bea": k, "industry": io[y]["names"][k], "firms": len(gi),
                         "markup": mu[n], "covered": k in cov, "sales_share": io[y]["lam"][n],
                         "cost_domar": lt[n],
                         "markup_p10": gi.mu_uc.quantile(0.1) if len(gi) else np.nan,
                         "markup_p90": gi.mu_uc.quantile(0.9) if len(gi) else np.nan,
                         "top_firm": gi.sort_values("revenue").entity.iloc[-1] if len(gi) else ""})
    pd.DataFrame(rows).round(5).to_csv(I.OUT / "industries.csv", index=False)

    # Figure 1: cumulative decomposition, user-cost markups (paper's Figure 4)
    d = dec[dec.series == "mu_uc"]
    years = [y0] + list(d.index)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for k, lab, c, ls in [("tfp_adjusted", "Distortion-adjusted Solow residual", "#222222", "-"),
                          ("ae_firm", "Allocative efficiency, firm level", "#c0392b", "-"),
                          ("technology", "Pure technology (residual)", "#d4a017", "-"),
                          ("ae_industry", "Allocative efficiency, industry level", "#c0392b", "--")]:
        ax.plot(years, [0] + list(d[k].cumsum() * 100), color=c, ls=ls, lw=2, label=lab)
    ax.axhline(0, color="#999999", lw=0.8)
    ax.set_ylabel("Cumulative change since 2011 (log points x 100)")
    ax.set_title("US TFP growth and its reallocation component, 2011-2023 (user-cost markups)")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(I.OUT / "cumulative.png", dpi=150)
    plt.close(fig)

    # Figure 2: between vs within (paper's Figure 3)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, lab, c in [("cum_dlog_markup", "Aggregate markup", "#222222"), ("cum_within", "Within firms", "#2e86c1"),
                      ("cum_between", "Between firms (reallocation)", "#c0392b")]:
        ax.plot(years, [0] + list(bw[k] * 100), color=c, lw=2, label=lab)
    ax.axhline(0, color="#999999", lw=0.8)
    ax.set_ylabel("Cumulative log change since 2011 (x 100)")
    ax.set_title("Change in the sales-weighted markup of US public companies (user-cost markups)")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(I.OUT / "markup_between_within.png", dpi=150)
    plt.close(fig)
    print("Wrote results/*.csv and results/*.png")


if __name__ == "__main__":
    main()
