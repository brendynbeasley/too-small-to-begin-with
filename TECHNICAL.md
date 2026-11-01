# Technical notes

This is the technical companion to the [README](README.md). It covers the data, the method, the full set of test
statistics and how to reproduce everything. Every table is in [results/FINDINGS.md](results/FINDINGS.md), and a
review of the original paper's methods is in [METHODS_REVIEW.md](METHODS_REVIEW.md).

## The original study

David Rezza Baqaee and Emmanuel Farhi, "Productivity and Misallocation in General Equilibrium," *Quarterly Journal
of Economics* 135(1), 2020, pp. 105–163 (NBER Working Paper 24007, revised October 2020). Using Compustat markups
inside the BEA input-output network, they report that improved allocative efficiency "accounts for about half of
aggregate TFP growth over the period 1997-2015," that the gain disappears when each industry is collapsed into a
representative firm, and that eliminating markups would raise TFP by about 15% (11% to 25% across markup series in
their Table 1).

## Headline results

All figures are cumulated log changes, 2011 to 2023, user-cost markups unless stated. Brackets are 95% intervals
from 200 company-level bootstrap draws.

| Quantity | Value |
|---|---|
| Distortion-adjusted TFP growth | 0.076 |
| Allocative efficiency, firm level | 0.053 [0.037, 0.069] |
| Share of TFP growth | 0.70 [0.49, 0.90] |
| Allocative efficiency, industry level | 0.065 [0.055, 0.083] |
| Within-industry reallocation term | −0.042 [−0.058, −0.029] |
| Same, accounting-profit markups: share of TFP growth | 0.59 [0.39, 0.83] |
| Oil, gas and refining at the aggregate markup: share | 0.37 |
| COGS reporters only, user cost: share | 0.08 |
| COGS-only markups (De Loecker–Eeckhout): share | 0.04 |
| All-operating-cost markups (Traina): share | 0.02 |

## Data

- **Company filings:** SEC Financial Statement Data Sets, quarterly files 2012q1 to 2025q3
  (`sec.gov/files/dera/data/financial-statement-data-sets/<quarter>.zip`), 10-K filings only, us-gaap tags,
  consolidated values (no co-registrant, no segment). Built by `src/fetch_sec.py` into
  `data/sec_firm_years.csv` (63,430 firm-years, 9,939 companies, fiscal years 2011–2023, committed).
- **Input-output tables:** BEA, `IOUse_Before_Redefinitions_PRO_1997-2023_Summary.xlsx` from AllTablesIO.zip
  (release of September 2024). 71 industries; dropping the five government industries, scrap and noncomparable
  imports leaves 66, the same count as the paper.
- **Growth accounting:** John Fernald's `quarterly_tfp.xlsx`, sheet `annual` (San Francisco Fed, produced October
  1, 2026): `dY`, `dhours`, `dLQ`, `dk`, `dtfp`.
- **Required return:** FRED `DFII10` (10-year TIPS yield, annual average) plus the implied equity risk premium
  (FCFE) from Aswath Damodaran's `histimpl.xls`.

## Method

Rules fixed before seeing results, following the paper's Section 7 and Appendix C wherever possible:

- Fiscal years follow the Compustat convention (years ending January–May belong to the prior year). Revenue is the
  largest of five revenue tags; operating income is `OperatingIncomeLoss`, else pretax income plus interest
  expense, else revenue minus `CostsAndExpenses`.
- Excluded, as in the paper: financial SIC codes 6000–6799, assets under $10 million, negative or missing book
  equity. Also excluded: non-positive revenue and operating income at least as large as revenue.
- Companies map to BEA summary industries through a SIC table in `src/inputs.py`. An industry's markup comes from
  its companies only if at least 3 are present in both years of a step and their combined revenue is at least 1%
  of BEA gross output; otherwise it takes the aggregate markup (the paper's rule for industries with no Compustat firms).
- Markups: user cost $`\mu_i = R_i/(R_i - \Pi_i + rK_i)`$ with $`K_i`$ net PP&E; accounting profits
  $`\mu_i = R_i/(R_i-\Pi_i)`$, with $`R_i`$ revenue and $`\Pi_i`$ operating income. Operating income is
  before income taxes, where the paper's user-cost series uses it after taxes, and the accounting-profit series uses
  reported depreciation, where the paper substitutes BEA industry depreciation rates.
  Extension: $`\mu_i = \theta_{I,t}R_i/X_i`$ with $`X_i`$ COGS, or all operating costs $`R_i-\Pi_i`$,
  and $`\theta_{I,t}`$ the industry-year median of $`X_i`$ over user-cost total cost.
- Markups and annual markup changes are winsorized at 5–95% by year (paper).
- Industry markups are harmonic sales-weighted means; $`\Omega`$ comes from the use table, $`\tilde\Omega=\operatorname{diag}(\mu)\Omega`$,
  and capital payments are gross operating surplus minus $`(1-1/\mu_I)`$ times sales, floored at zero (paper).
- Each step uses only companies present in both years.
- Firm-years with no net PP&E tag (933 of 35,002, General Motors among them) get a zero capital charge, so their
  user-cost markup equals the accounting-profit one.

The objects computed each year are

```math
\tilde\lambda' = b'(I-\tilde\Omega)^{-1},\qquad
\tilde\lambda_i = s_i\,\tilde\lambda_{I(i)},\qquad
\tilde\Lambda_f = \sum_I \tilde\lambda_I\,\mu_I\,\Omega_{If}
```

```math
\Delta\text{AE}_t = -\sum_i \tilde\lambda_{i,t-1}\Delta\log\mu_{i,t} - \sum_f \tilde\Lambda_{f,t-1}\Delta\log\Lambda_{f,t},
\qquad
\Delta\log\text{TFP}_t = \Delta\log Y_t - \sum_f \tilde\Lambda_{f,t-1}\Delta\log V_{f,t}
```

where $`b`$ is final-demand shares, $`s_i`$ the firm's share of its industry's public sales, $`V_f`$ the quantity of
factor $`f`$ (labor input is hours plus labor quality, capital is Fernald's capital services), and
$`L_i = 1-1/\mu_i`$ the Lerner index. The within-industry reallocation term is
$`\sum_t\sum_i \tilde\lambda_{I}\mu_I\,\Delta s_{i,t}\,(1-1/\mu_{i,t-1})`$. The share regression is

```math
\Delta\log s_{i,t} = \alpha_{I(i),t} + \beta L_{i,t-1} + \varepsilon_{i,t}
```

with industry-by-year fixed effects, share changes winsorized 5–95% by year, standard errors clustered by company.

## Test statistics

Share regression (`results/share_regression.csv`), 28,708 firm-years for the total-cost series and 21,244 for the
cost-share series:

| Markup | Weights | β | SE | 95% CI | p |
|---|---|---|---|---|---|
| User cost | Equal | −0.0209 | 0.0017 | [−0.0242, −0.0176] | < 0.001 |
| User cost | Sales | −0.0790 | 0.0182 | [−0.1147, −0.0433] | < 0.001 |
| Accounting profits | Equal | −0.0208 | 0.0017 | [−0.0241, −0.0175] | < 0.001 |
| Accounting profits | Sales | −0.0699 | 0.0199 | [−0.1088, −0.0310] | < 0.001 |
| COGS only | Equal | 0.0269 | 0.0054 | [0.0162, 0.0375] | < 0.001 |
| COGS only | Sales | 0.0228 | 0.0079 | [0.0073, 0.0383] | 0.004 |
| All operating costs | Equal | −0.0459 | 0.0039 | [−0.0536, −0.0382] | < 0.001 |
| All operating costs | Sales | 0.0065 | 0.0154 | [−0.0238, 0.0367] | 0.67 |

Robustness (`results/robustness.csv`), user cost, cumulated allocative efficiency and share of TFP growth:
benchmark 0.053 (70%); oil, gas and refining at the aggregate markup 0.028 (37%); loss-making firm-years dropped
0.014 (17%); negative-equity firms kept 0.059 (77%); winsorized 1–99% 0.097 (127%).

Aggregate markup (`results/markup_between_within.csv`): 1.099 in 2011; cumulated log change −0.025, of which within
firms −0.012 and between firms −0.013.

## Reproducing the results

```bash
pip install -r requirements.txt
python src/fetch_sec.py        # optional: rebuilds data/sec_firm_years.csv (downloads about 5 GB)
python src/misallocation.py    # about 8 minutes, most of it the bootstrap
```

The second command runs offline from the committed files.

## Repository layout

| Path | What it is |
|---|---|
| `src/fetch_sec.py` | Builds the firm-year panel from SEC filings |
| `src/inputs.py` | Sample rules, markups, BEA tables, TFP series, SIC-to-BEA map |
| `src/misallocation.py` | Decomposition, bootstrap, regression, robustness, tables, figures |
| `data/sec_firm_years.csv` | Firm-year panel |
| `data/raw/` | BEA use tables, Fernald TFP, TIPS yield, Damodaran premiums |
| `results/` | Every CSV and figure cited in the README |

## References

- Baqaee, D. R. & Farhi, E. (2020). Productivity and misallocation in general equilibrium. *QJE* 135(1).
- Basu, S. (2019). Are price-cost markups rising in the United States? *Journal of Economic Perspectives* 33(3).
- De Loecker, J., Eeckhout, J. & Unger, G. (2020). The rise of market power and the macroeconomic implications.
  *QJE* 135(2).
- Fernald, J. (2014). A quarterly, utilization-adjusted series on total factor productivity. FRBSF WP 2012-19.
- Gutiérrez, G. & Philippon, T. (2016). Investment-less growth. NBER WP 22897.
- Harberger, A. C. (1954). Monopoly and resource allocation. *AER Papers and Proceedings* 44.
- Hulten, C. R. (1978). Growth accounting with intermediate inputs. *Review of Economic Studies* 45(3).
- Traina, J. (2018). Is aggregate market power increasing? Production trends using financial statements.
  Stigler Center Working Paper.
