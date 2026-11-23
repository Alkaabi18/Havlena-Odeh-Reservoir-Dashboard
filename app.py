from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ho_engine import read_input_workbook, calculate_havlena_odeh, convert_inputs_to_canonical

st.set_page_config(page_title="Havlena–Odeh Dashboard", page_icon="🛢️", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1450px;}
      div[data-testid="stMetric"] {background: #f4f7fa; border: 1px solid #e0e7ef; padding: 14px 16px; border-radius: 10px;}
      div[data-testid="stMetricLabel"] {color: #425466;}
      .small-note {font-size: 0.88rem; color: #586879;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛢️ Havlena–Odeh Material-Balance Dashboard")
st.caption("Oil reservoir • gas-cap drive • straight-line interpretation")

# The selectors define the units used by every numeric value in the corresponding
# Excel column / parameter. The calculation engine converts all values to canonical
# units before any material-balance term or regression is calculated.
with st.sidebar:
    st.header("Input workbook")
    uploaded = st.file_uploader("Upload your Excel workbook (.xlsx)", type=["xlsx", "xlsm"])
    st.divider()
    st.subheader("Input units")
    st.caption("Choose the units that are actually used in your Excel workbook. Each selection applies to the entire column or parameter.")

    with st.expander("Production / PVT column units", expanded=True):
        p_unit = st.selectbox("Average reservoir pressure, p", ["psi", "kPa", "MPa", "bar"], index=0)
        np_unit = st.selectbox("Cumulative oil produced, Np", ["STB", "MSTB", "MMSTB"], index=0)
        gp_unit = st.selectbox("Cumulative gas produced, Gp", ["scf", "Mscf", "MMscf", "Bscf / MMMSCF (10⁹ scf)"], index=0, help="Bscf / MMMSCF means 10^9 standard cubic feet.")
        bo_unit = st.selectbox("Oil formation volume factor, Bo", ["rb/STB", "bbl/STB", "ft³/STB"], index=0)
        bg_unit = st.selectbox("Gas formation volume factor, Bg", ["rb/scf", "ft³/scf", "rb/Mscf", "ft³/Mscf"], index=0)
        rs_unit = st.selectbox("Solution gas-oil ratio, Rs", ["scf/STB", "Mscf/STB"], index=0)

    with st.expander("Initial reservoir parameter units", expanded=True):
        pi_unit = st.selectbox("Initial pressure, pi", ["psi", "kPa", "MPa", "bar"], index=0)
        boi_unit = st.selectbox("Initial oil FVF, Boi", ["rb/STB", "bbl/STB", "ft³/STB"], index=0)
        bgi_unit = st.selectbox("Initial gas FVF, Bgi", ["rb/scf", "ft³/scf", "rb/Mscf", "ft³/Mscf"], index=0)
        rsi_unit = st.selectbox("Initial solution GOR, Rsi", ["scf/STB", "Mscf/STB"], index=0)
        swc_unit = st.selectbox("Connate water saturation, Swc", ["fraction (0–1)", "percent (%)"], index=0)
        cw_unit = st.selectbox("Water compressibility, Cw", ["psi⁻¹", "kPa⁻¹", "MPa⁻¹", "bar⁻¹"], index=0)
        cf_unit = st.selectbox("Formation compressibility, Cf", ["psi⁻¹", "kPa⁻¹", "MPa⁻¹", "bar⁻¹"], index=0)

    use_compressibility = st.checkbox(
        "Include connate-water and formation compressibility",
        value=True,
        help="Uses Swc, Cw, and Cf from the Initial_Parameters sheet after converting their selected units.",
    )
    st.caption("Pressure and compressibility units are converted internally so that the pressure and Cw/Cf units are consistent.")

input_units = {
    "p": p_unit,
    "Np": np_unit,
    "Gp": gp_unit,
    "Bo": bo_unit,
    "Bg": bg_unit,
    "Rs": rs_unit,
    "pi": pi_unit,
    "Boi": boi_unit,
    "Bgi": bgi_unit,
    "Rsi": rsi_unit,
    "Swc": swc_unit,
    "Cw": cw_unit,
    "Cf": cf_unit,
}

if uploaded is None:
    st.info("Upload the provided Excel input template or a workbook with the required production/PVT and initial-parameter sheets.")
    st.markdown(
        "**Required production/PVT columns:** `p`, `Np`, `Gp`, `Bo`, `Bg`, `Rs`.\n\n"
        "**Required initial parameters:** `pi`, `Boi`, `Bgi`, `Rsi`, `Swc`, `Cw`, `Cf`."
    )
    st.markdown(
        "The unit selectors in the sidebar let you use common field and engineering units. "
        "All uploaded values are converted internally to psi, STB, scf, rb/STB, rb/scf, "
        "scf/STB, saturation fraction, and psi⁻¹ before calculation."
    )
    st.stop()

try:
    production, params, production_sheet, parameter_sheet = read_input_workbook(uploaded)
    _, canonical_params, selected_units = convert_inputs_to_canonical(production, params, input_units)
    calc, result = calculate_havlena_odeh(
        production,
        params,
        include_compressibility=use_compressibility,
        input_units=input_units,
    )
except Exception as exc:
    st.error(f"Could not process the uploaded workbook: {exc}")
    st.stop()

st.success(f"Loaded production sheet **{production_sheet}** and parameter sheet **{parameter_sheet}**.")
st.info(
    "Input units converted internally to: p/pi = psi; Np = STB; Gp = scf; "
    "Bo/Boi = rb/STB; Bg/Bgi = rb/scf; Rs/Rsi = scf/STB; Swc = fraction; Cw/Cf = psi⁻¹. "
    "The unit selections apply to every value in the corresponding field."
)

# Headline results
N = result["N_STB"]
m = result["m"]
G = result["G_scf"]
r2 = result["R2"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Original oil in place, N", f"{N/1e6:,.3f} MMSTB", help=f"{N:,.0f} STB")
k2.metric("Gas-cap ratio, m", f"{m:,.4f}")
k3.metric("Initial gas-cap gas, G", f"{G/1e9:,.3f} Bscf", help=f"{G:,.0f} scf")
k4.metric("Regression R²", f"{r2:,.4f}" if np.isfinite(r2) else "N/A")

if result["warnings"]:
    for message in result["warnings"]:
        st.warning(message)

st.caption(
    f"Regression uses {result['n_valid']} of {result['n_total']} rows. "
    "The fitted line is y = N + (N·m)x."
)

tab_overview, tab_plot, tab_table, tab_method = st.tabs(
    ["Overview", "H–O straight-line plot", "Calculations & input data", "Method & assumptions"]
)

with tab_overview:
    left, right = st.columns([1.05, 1])
    with left:
        st.subheader("Estimated reservoir parameters")
        display = pd.DataFrame(
            [
                ["N", N, "STB", "H–O regression intercept"],
                ["m", m, "dimensionless", "Slope / intercept"],
                ["G", G, "scf", "m × N × Boi / Bgi"],
                ["Nm", result["slope_Nm_STB"], "STB", "H–O regression slope"],
                ["R²", r2, "dimensionless", "Coefficient of determination"],
            ],
            columns=["Parameter", "Calculated value", "Unit", "Interpretation"],
        )
        st.dataframe(display, hide_index=True, use_container_width=True)
        st.download_button(
            "Download calculation table (CSV)",
            data=calc.to_csv(index=False).encode("utf-8-sig"),
            file_name="havlena_odeh_calculations.csv",
            mime="text/csv",
        )
    with right:
        st.subheader("Production history")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=calc["Np"], y=calc["p"], mode="lines+markers", name="Average reservoir pressure"))
        fig.update_layout(
            xaxis_title="Cumulative oil produced, Np (STB)",
            yaxis_title="Average reservoir pressure, p (psi)",
            yaxis=dict(autorange="reversed"),
            height=390,
            margin=dict(l=20, r=20, t=25, b=20),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_plot:
    st.subheader("Havlena–Odeh straight-line interpretation")
    valid = calc.loc[calc["Included"]].copy()
    x = valid["HO_x"].to_numpy()
    xline = np.linspace(float(np.min(x)), float(np.max(x)), 100)
    yline = N + result["slope_Nm_STB"] * xline
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=valid["HO_y"], mode="markers+text", name="Calculated history points",
            text=[f"Row {int(v)}" for v in valid["Excel row"]], textposition="top center",
            marker=dict(size=10),
            customdata=np.column_stack([valid["p"], valid["Np"]]),
            hovertemplate="x=%{x:.5g}<br>y=%{y:,.5g}<br>p=%{customdata[0]:,.0f} psi<br>Np=%{customdata[1]:,.0f} STB<extra></extra>",
        )
    )
    fig.add_trace(go.Scatter(x=xline, y=yline, mode="lines", name="Least-squares fit", line=dict(width=3)))
    fig.update_layout(
        xaxis_title="x = (Eg + Efw₀) / (Eo + Efw₀)",
        yaxis_title="y = F / (Eo + Efw₀) (STB)",
        height=570,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=30, r=25, t=40, b=35),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        f"**Regression equation:** y = {result['slope_Nm_STB']:,.4g} x + {N:,.4g} "
        f"(R² = {r2:.5f})"
    )
    st.markdown(
        "The y-intercept gives **N**. The slope gives **N·m**, therefore "
        "**m = slope / intercept**."
    )

with tab_table:
    st.subheader("Calculated terms for each Excel row")
    st.caption("Displayed pressure, production, FVF, and GOR values are shown after conversion to the dashboard's canonical units. Rows not used in regression are retained and marked with an exclusion reason.")
    st.dataframe(calc, use_container_width=True, hide_index=True)
    excluded = calc.loc[~calc["Included"]]
    if not excluded.empty:
        with st.expander("Show excluded rows"):
            st.dataframe(excluded[["Excel row", "p", "Np", "Gp", "Reason"]], use_container_width=True, hide_index=True)
    with st.expander("Selected workbook units and internal units"):
        unit_rows = [
            ("p", p_unit, "psi"), ("Np", np_unit, "STB"), ("Gp", gp_unit, "scf"),
            ("Bo", bo_unit, "rb/STB"), ("Bg", bg_unit, "rb/scf"), ("Rs", rs_unit, "scf/STB"),
            ("pi", pi_unit, "psi"), ("Boi", boi_unit, "rb/STB"), ("Bgi", bgi_unit, "rb/scf"),
            ("Rsi", rsi_unit, "scf/STB"), ("Swc", swc_unit, "fraction"),
            ("Cw", cw_unit, "psi⁻¹"), ("Cf", cf_unit, "psi⁻¹"),
        ]
        st.dataframe(pd.DataFrame(unit_rows, columns=["Input field", "Selected workbook unit", "Calculation unit"]), hide_index=True, use_container_width=True)

with tab_method:
    st.subheader("Equations used")
    st.latex(r"R_p = \frac{G_p}{N_p}")
    st.latex(r"F = N_p\left[B_o + (R_p-R_s)B_g\right]")
    st.latex(r"E_o = (B_o-B_{oi}) + (R_{si}-R_s)B_g")
    st.latex(r"E_g = B_{oi}\left(\frac{B_g}{B_{gi}}-1\right)")
    st.latex(r"E_{fw0}=B_{oi}\left(\frac{C_wS_{wc}+C_f}{1-S_{wc}}\right)(p_i-p)")
    if use_compressibility:
        st.latex(r"\frac{F}{E_o+E_{fw0}} = N + Nm\left(\frac{E_g+E_{fw0}}{E_o+E_{fw0}}\right)")
        st.markdown("The full formation/connate-water expansion is **Efw = (1 + m) Efw₀**. Moving the terms involving m to the x-axis gives the straight-line form above.")
    else:
        st.latex(r"\frac{F}{E_o} = N + Nm\left(\frac{E_g}{E_o}\right)")
        st.markdown("Compressibility expansion was switched off for this run, so Efw₀ = 0.")
    st.latex(r"m=\frac{\text{slope}}{\text{intercept}},\qquad G=\frac{mNB_{oi}}{B_{gi}}")

    st.subheader("Assumptions and limitations")
    st.markdown(
        """
        - No aquifer influx: **We = 0**.
        - Produced water is neglected: **Wp = 0**. The supplied data do not include Wp or Bw.
        - No water or gas injection is modelled.
        - All selected workbook units are converted to canonical calculation units before computing material-balance terms.
        - The analysis is intended for a conventional oil reservoir with an initial gas cap and data that follow the assumed material-balance model.
        - At least three valid depleted-state rows are required. The initial point (commonly Np = 0) is not a regression point.
        """
    )
    st.subheader("Data-quality notes")
    st.write(
        f"Initial parameters after conversion: pi={canonical_params['pi']:,.6g} psi; "
        f"Boi={canonical_params['Boi']:.8g} rb/STB; Bgi={canonical_params['Bgi']:.8g} rb/scf; "
        f"Rsi={canonical_params['Rsi']:,.6g} scf/STB; Swc={canonical_params['Swc']:.6g}; "
        f"Cw={canonical_params['Cw']:.6g} psi⁻¹; Cf={canonical_params['Cf']:.6g} psi⁻¹."
    )
    st.markdown(
        "**Method reference:** [whitson⁺ — Static Material Balance](https://manual.whitson.com/modules/material-balance/static_mb/) "
        "(Havlena–Odeh expansion terms and material-balance formulation)."
    )

st.divider()
st.caption("Educational engineering tool. Verify units, reservoir assumptions, pressure averaging, and PVT consistency before using estimates for operational or reserves decisions.")
