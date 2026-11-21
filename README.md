# Havlena–Odeh Reservoir Material-Balance Dashboard

An interactive Streamlit dashboard for an oil reservoir with an initial gas cap. Upload an Excel workbook containing production/PVT history and initial reservoir parameters. The dashboard calculates **N**, **m**, and initial gas-cap gas **G**, plots the Havlena–Odeh straight line, reports R², and exposes intermediate calculations and data-quality warnings.

## Files

- `app.py` — interactive Streamlit dashboard.
- `ho_engine.py` — Excel parsing, unit conversion, calculations, and regression.
- `Havlena_Odeh_Input_Template.xlsx` — sample input workbook. Replace its synthetic data with your own values while keeping the sheet/column structure.
- `test_ho_engine.py` — regression test using the synthetic template dataset.
- `requirements.txt` — Python dependencies.

## 1. Install

Use Python 3.10 or newer. Open Command Prompt / Terminal in this folder and run:

```bash
python -m venv .venv
```

Activate the environment:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install the packages:

```bash
pip install -r requirements.txt
```

## 2. Run the dashboard

```bash
streamlit run app.py
```

Your browser should open the local dashboard. Upload `Havlena_Odeh_Input_Template.xlsx` to check the synthetic example, then upload your own workbook.

## 3. Excel input format

The workbook should contain the following sheets (sheet names may vary; the dashboard detects the columns and parameter table):

### Production/PVT sheet

| Required column | Meaning | Required unit |
|---|---|---|
| `p_psi` | Average reservoir pressure, p | psi |
| `Np_STB` | Cumulative oil produced, Np | STB |
| `Gp_scf` | Cumulative gas produced, Gp | scf by default; dashboard can convert Mscf or MMscf |
| `Bo_rb_per_STB` | Oil formation volume factor, Bo | rb/STB |
| `Bg_rb_per_scf` | Gas formation volume factor, Bg | rb/scf |
| `Rs_scf_per_STB` | Solution gas-oil ratio, Rs | scf/STB |

One row is one pressure/production/PVT observation. Do not include merged cells in the data table. Keep the headings in the first row. If Gp is not in scf, choose its actual unit in the app sidebar.

### Initial-parameter sheet

Use two columns named `Parameter` and `Value` (a third `Unit` column is optional):

| Parameter key | Meaning | Unit |
|---|---|---|
| `pi_psi` | Initial reservoir pressure, pi | psi |
| `Boi_rb_per_STB` | Initial oil FVF, Boi | rb/STB |
| `Bgi_rb_per_scf` | Initial gas FVF, Bgi | rb/scf |
| `Rsi_scf_per_STB` | Initial solution GOR, Rsi | scf/STB |
| `Swc_fraction` | Connate water saturation, Swc | fraction (0–1) |
| `Cw_per_psi` | Water compressibility, Cw | psi^-1 |
| `Cf_per_psi` | Formation compressibility, Cf | psi^-1 |

Pressure and compressibility units must match. The provided template demonstrates the exact format accepted by the app.

## 4. Equations and straight-line interpretation

The app calculates cumulative producing GOR and underground withdrawal:

\[
R_p=G_p/N_p,\qquad F=N_p[B_o+(R_p-R_s)B_g]
\]

Oil/solution-gas expansion and gas-cap expansion are:

\[
E_o=(B_o-B_{oi})+(R_{si}-R_s)B_g
\]

\[
E_g=B_{oi}(B_g/B_{gi}-1)
\]

For connate-water and rock compressibility, define:

\[
E_{fw0}=B_{oi}\left(\frac{C_wS_{wc}+C_f}{1-S_{wc}}\right)(p_i-p)
\]

The full expansion term is \(E_{fw}=(1+m)E_{fw0}\). Starting from

\[
F=N(E_o+mE_g+E_{fw})
\]

and collecting terms gives the straight-line form used by the dashboard:

\[
\frac{F}{E_o+E_{fw0}}=N+Nm\left(\frac{E_g+E_{fw0}}{E_o+E_{fw0}}\right)
\]

Therefore, when plotting \(y=F/(E_o+E_{fw0})\) against \(x=(E_g+E_{fw0})/(E_o+E_{fw0})\):

- y-intercept = **N** (STB)
- slope = **Nm** (STB)
- **m = slope / intercept** (dimensionless)
- **G = m N Boi / Bgi** (scf)

When the compressibility checkbox is off, the app uses the classical reduced plot \(F/E_o=N+Nm(E_g/E_o)\).

## 5. Important model assumptions

The question does not provide produced-water history, water FVF, injection data, or aquifer influx. Therefore, this dashboard uses **Wp = 0**, **We = 0**, and no injection. It includes connate-water and formation compressibility when the sidebar option is enabled. If the reservoir has significant water production or water drive, the current three-variable model is not sufficient; extend the input data and material-balance equation before interpreting N, m, or G.

The dashboard requires at least three valid depleted-state rows, excludes rows with Np <= 0 and invalid/non-positive expansion denominators, and reports excluded rows. Low R² or negative fitted m should prompt a review of data and assumptions, not be hidden or automatically corrected.

## 6. Test the supplied sample

Run:

```bash
python -m unittest test_ho_engine.py
```

The synthetic workbook is designed to recover approximately:

- N = 10,000,000 STB
- m = 0.25
- G = 3,906,250,000 scf
- R² = 1.0

These are software test values only, not field/reservoir estimates.

## Method reference

- whitson⁺, *Static Material Balance* — Havlena–Odeh expansion terms and compact material-balance formulation: https://manual.whitson.com/modules/material-balance/static_mb/
- HSM University, *The General Material Balance Equation*: https://www.hsmuniversity.org/ca/course/pet-320-reservoir-engineering-i/lesson-5-the-general-material-balance-equation
