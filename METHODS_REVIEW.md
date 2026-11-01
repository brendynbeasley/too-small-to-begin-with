# Methods review of Baqaee and Farhi (2020)

**Paper.** David Rezza Baqaee and Emmanuel Farhi, "Productivity and Misallocation in General Equilibrium,"
*Quarterly Journal of Economics* 135(1), 2020, pp. 105–163, doi 10.1093/qje/qjz030. Circulated as NBER Working
Paper 24007 (November 2017, revised October 2020).

**Statistical focus.** Two quantitative claims carry the paper's applied half. The first is that improvements in
allocative efficiency, from market share moving toward high-markup firms, account for about half of aggregate TFP
growth in the United States over 1997–2015 (Section 7.2, Figure 4). The second is that eliminating the misallocation
caused by markups would raise aggregate TFP by about 15% (abstract), with a range of 11% to 25% across markup
series in 2015 (Section 7.3, Table 1).

**Review standard.** For the theory, internal consistency of the formal results, explicit assumptions and the
testability of predictions. For the applied sections, current AEA Data and Code Availability Policy expectations and
standard reporting of estimates, uncertainty and sample construction.

**What was read.** The full text of NBER Working Paper 24007, revised October 2020, including the online appendix
(Appendices A to J), from nber.org. The QJE publisher abstract and bibliographic record were checked for the
citation and the headline numbers. The published QJE typeset version itself was not read, so page references
below are to the NBER revision.

---

## Methods summary

**Research design.** The paper is primarily theoretical. It derives a first-order decomposition of output changes in
a general-equilibrium economy with arbitrary input-output linkages and wedges (Theorem 1, equation 4) into a
pure-technology term and an allocative-efficiency term, then a growth-accounting version (Proposition 1, equation 7)
and a second-order "distance to the frontier" formula (Proposition 5). The applied sections are proof-of-concept
calculations that plug US data into these formulas; the authors describe them as tentative.

**Sampling strategy.** Not a sample in the statistical sense. The firm data are all Compustat firms from 1997
onward, after exclusions; the industry data are the universe of BEA annual input-output tables. No inference to a
population is attempted.

**Sample size.** 66 BEA industries, 1997–2015 (Section 7.1). The number of Compustat firms or firm-years after
exclusions is not reported in the text I read.

**Inclusion and exclusion criteria.** Appendix C.2 drops firm-years with assets under $10 million, negative book or
market value, missing year, assets or book liabilities; firms with BEA code 999; and financials (SIC 6000–6999 or
NAICS 520–525). BEA government, scrap and noncomparable-import industries are dropped. Industries with no
Compustat firms are assigned the aggregate markup.

**Independent and dependent variables.** The object of interest is the cumulated distortion-adjusted Solow residual
(output growth from the San Francisco Fed series minus cost-share-weighted growth of labor and capital) and its
split into technology and allocative efficiency. Inputs are firm sales shares, firm markups under three methods
(user cost, accounting profits, production-function estimation), BEA input-output shares and factor income shares.

**Statistical methods.** Deterministic accounting identities applied to the data, plus a calibrated nested-CES
model for the counterfactual (elasticities 0.5, 0.9, 0.2, 1 and 8, Section 7.3). The production-function markups
use Olley-Pakes estimation with the Ackerberg-Caves-Frazer correction on three-year rolling windows (Appendix
C.2.3). Markups and markup changes are winsorized at the 5th and 95th percentiles by year.

**Reported effect sizes.** Shares of cumulated TFP growth (about 50%) and percentage TFP gains from removing
markups (Tables 1 and 2). See the extraction table.

**Confidence intervals.** None are reported for any applied quantity.

**P-values.** Not applicable; no hypothesis tests are performed.

**Missing data treatment.** Industries without Compustat coverage take the aggregate markup; negative capital
payments (gross operating surplus minus imputed profits) and negative input-output entries are set to zero
(Appendix C.1). Firms without NAICS codes are mapped through the modal NAICS of firms sharing their SIC code.

**Stated limitations.** The authors list three (Introduction, Section 7.1): firm-level input-output links are
imputed from industry tables by assuming identical production functions within an industry; Compustat may not
represent the economy; and markups are assumed to be the only wedges. They add that the numbers "should be
interpreted with care since the data is imperfect and requires substantial imputation" (abstract).

---

## Statistics extraction table

| Statistic | Value and unit | Source location | What it measures | What it does not establish |
|---|---|---|---|---|
| Share of TFP growth from allocative efficiency | about 50% of cumulated growth | Abstract; Introduction item 1; Section 7.2; Figure 4 | Cumulated allocative-efficiency term divided by cumulated distortion-adjusted Solow residual, 1997 to 2014/2015, user-cost markups | That reallocation caused growth in a counterfactual sense; it is a first-order accounting split with technology measured as a residual |
| Same exercise, industry-level markups | Contribution "drastically reduced and even flip[s] signs" | Section 7.2; Figure 5 | The decomposition when each industry is one representative firm | A precise number; the text gives none, only the figure |
| Same exercise, PF and AP markups | Large at firm level, negligible at industry level; "magnitudes are somewhat different" | Section 7.2; Appendix A Figures 6 and 7 | Robustness of the sign to the markup method | The size of the share under those methods, which is only shown graphically |
| Average markup levels | about 5% (UC), 10% (AP), 16% (PF) | Section 7.1 | Typical markup level by method | Which method is right; the methods differ by a factor of three |
| Gains from eliminating markups, 2015 | 13% (UC), 11% (AP), 25% (PF) of TFP | Table 1 | Second-order distance to the efficient frontier in the calibrated model | A dynamic welfare gain; entry and innovation responses are excluded (footnote 2) |
| Gains from eliminating markups, 1997 | 3% (UC), 5% (AP), 23% (PF) | Table 1 | Same, start of sample | That misallocation rose for one cause; dispersion of measured markups also depends on method |
| Abstract headline gain | about 15% | Abstract | A summary of Table 1 | It matches none of the three Table 1 entries exactly |
| Calibration sensitivity | 0.7% to 29% depending on specification | Table 2 | Gains under Cobb-Douglas, no input-output links, sectoral data, lower within-industry elasticity | Which elasticity is right; xi = 8 versus 4 roughly halves the answer |
| Harberger comparison | "two orders of magnitude" above 0.1% | Abstract; Section 7.3 | Ratio of the paper's estimate to Harberger (1954) | A like-for-like comparison; the sectoral version of the model gives 0.7% to 4% |

---

## Interpretation notes

The theory is internally consistent and its assumptions are stated: constant returns (with fixed factors standing
in for decreasing returns), wedges rebated lump sum, a homothetic final-demand aggregator, and inelastic factor
supply in the baseline. Theorem 1 nests Hulten's theorem, and the horizontal and vertical examples in Section 2.4
show clearly when each part of the decomposition is zero.

The applied "about 50%" is a ratio of two cumulated sums, and the technology term is a residual. Any error in the
allocative-efficiency term (from markup measurement, from imputed firm-level input-output links, or from
non-markup wedges the authors set aside) moves one-for-one into the technology term. The share therefore inherits
all the measurement uncertainty in markups, and no interval is offered.

The sign of the result rests on a fact the paper documents separately: the rise in the sales-weighted average markup
is mostly a between-firm composition effect (Figure 3). If high measured markups partly reflect unmeasured capital
(intangibles, R&D treated as an expense), then reallocation toward those firms would be reallocation toward
capital-intensive firms rather than toward under-producing ones, and the allocative-efficiency gain would be
overstated. The paper acknowledges that the user-cost method "assumes that all inputs are flexible" (Section 7.1)
and that identifying fixed or quasi-fixed factors is the most challenging step (Section 6); it does not test this
alternative directly.

There are small reporting inconsistencies between sections. The decomposition period is given as 1997–2015 in the
abstract, 1997–2014 in the Introduction, and the figures run to 2014. Table 1 is labelled 2015 while the text
discussing it says "13% in 2014". The abstract's "about 15%" is a rounded summary across series rather than a
reported entry. None of these changes a conclusion, but they make exact citation harder.
The Introduction also gives the 2015 gain as "about 10-25%". Because the working paper was revised several times
between 2017 and 2020, numbers should be cited by version.

Reporting gaps, kept separate from any claim of error: the firm count after exclusions is not given; the benchmark
user-cost markups come from Gutiérrez and Philippon's replication files (Appendix C.2.2) rather than being built
in the paper; no standard errors,
bootstrap or sensitivity bands accompany Figure 4. I found no published correction or comment documenting an
analytical error.

My own rerun in this repository uses free SEC filings for 2011–2023 rather than Compustat for 1997–2015, an
approximate user cost, and SIC-to-BEA mapping by judgment. It is a modern version of the same calculation and
cannot be read as a reproduction of the paper's numbers.

---

## Unanswered questions

How many firm-years enter each year's calculation, and how much of each BEA industry's sales do Compustat firms
cover? Coverage matters because within-industry shares are rescaled to the BEA total.

How sensitive is the 50% share to the winsorization rule, to the treatment of industries without Compustat firms,
and to clipping negative capital payments at zero?

What share of the allocative-efficiency term comes from foreign sales of US multinationals, which enter Compustat
revenue but not US gross output?

Would treating R&D and other intangible investment as capital, rather than as current cost, preserve the positive
correlation between initial markups and subsequent share growth?

How large is the second-order error in the first-order decomposition at annual frequency, given that markups and
shares move a lot in some years?

---

## Items requiring expert verification

The mapping of firms to BEA industries and the construction of the firm-level cost-based input-output matrix from
industry tables (Section 7.1) should be checked by someone with access to Compustat and the authors' code.

The user-cost markups depend on industry risk premia from IBES analyst forecasts (Appendix C.2.2); a finance
specialist should judge whether those premia are stable enough to support year-to-year changes in markups.

The production-function markups use COGS as the flexible input with Olley-Pakes estimation; Gandhi, Navarro and
Rivers (2020) and Bond, Hashemi, Kaplan and Zoch (2021) argue that output elasticities are poorly identified in this
setting, and an econometrician should assess how much that affects the PF column of Tables 1 and 2.

The choice of the within-industry elasticity of substitution (8, or 4 as an alternative) drives the size of the
gains in Table 2, and an industrial-organization economist should judge which range is credible industry by
industry.
