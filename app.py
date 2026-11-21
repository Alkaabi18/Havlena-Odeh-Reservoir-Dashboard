from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ho_engine import read_input_workbook, calculate_havlena_odeh

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

with st.sidebar:
    st.header("Input workbook")
    uploaded = st.file_uploader("Upload your Excel workbook (.xlsx)", type=["xlsx", "xlsm"])
    st.divider()
    st.subheader("Input interpretation")
    gas_unit = st.selectbox(
        "Unit used by the Gp column",
        ["scf", "Mscf", "MMscf"],
        index=0,
        help="Gp is converted to scf internally. Rs must be scf/STB and Bg must be rb/scf.",
    )
    use_compressibility = st.checkbox(
        "Include connate-water and formation compressibility",
        value=True,
        help="Uses the supplied Swc, Cw, and Cf values in the H–O straight-line transform.",
    )
    st.caption("Pressure must be in psi when Cw and Cf are in psi⁻¹.")

if uploaded is None:
    st.info("Upload the provided Excel input template or a workbook with the required production/PVT and initial-parameter sheets.")
    st.markdown("**Required production/PVT columns:** `p`, `Np`, `Gp`, `Bo`, `Bg`, `Rs`.\n\n**Required initial parameters:** `pi`, `Boi`, `Bgi`, `Rsi`, `Swc`, `Cw`, `Cf`.")
    st.markdown("Use the supplied template to avoid header and unit mismatches. The workbook must contain a production sheet and a separate Parameter/Value table.")
    st.stop()

try:
    production, params, production_sheet, parameter_sheet = read_input_workbook(uploaded)
    calc, result = calculate_havlena_odeh(
        production, params, gas_unit=gas_unit, include_compressibility=use_compressibility
    )
except Exception as exc:
    st.error(f"Could not process the uploaded workbook: {exc}")
    st.stop()

st.success(f"Loaded production sheet **{production_sheet}** and parameter sheet **{parameter_sheet}**.")

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
    st.caption("Rows not used in the regression are retained and marked with an exclusion reason.")
    preferred = [
        "Excel row", "p", "Np", "Gp", "Gp_scf_used", "Bo", "Bg", "Rs", "Rp_scf_per_STB",
        "F_rb", "Eo_rb_per_STB", "Eg_rb_per_STB", "Efw0_rb_per_STB",
        "Expansion_denominator", "HO_x", "HO_y", "Fitted_HO_y", "Residual", "Included", "Reason",
    ]
    st.dataframe(calc[preferred], use_container_width=True, hide_index=True)
    excluded = calc.loc[~calc["Included"]]
    if not excluded.empty:
        with st.expander("Show excluded rows"):
            st.dataframe(excluded[["Excel row", "p", "Np", "Gp", "Reason"]], use_container_width=True, hide_index=True)

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
        - Pressure is average reservoir pressure in psi; Cw and Cf must be in psi⁻¹.
        - Np is in STB; Gp is interpreted using the selected gas unit; Rs is in scf/STB; Bo/Boi are in rb/STB; Bg/Bgi are in rb/scf.
        - The analysis is intended for a conventional oil reservoir with an initial gas cap and data that follow the assumed material-balance model.
        - At least three valid depleted-state rows are required. The initial point (commonly Np = 0) is not a regression point.
        """
    )
    st.subheader("Data-quality notes")
    st.write(
        f"Initial parameters read from the workbook: pi={params['pi']:,.4g} psi, "
        f"Boi={params['Boi']:,.6g} rb/STB, Bgi={params['Bgi']:,.6g} rb/scf, "
        f"Rsi={params['Rsi']:,.4g} scf/STB, Swc={params['Swc']:,.4g}, "
        f"Cw={params['Cw']:.4g} psi⁻¹, Cf={params['Cf']:.4g} psi⁻¹."
    )
    st.markdown(
        "**Method reference:** [whitson⁺ — Static Material Balance](https://manual.whitson.com/modules/material-balance/static_mb/) "
        "(Havlena–Odeh expansion terms and material-balance formulation)."
    )

st.divider()
st.caption("Educational engineering tool. Verify units, reservoir assumptions, pressure averaging, and PVT consistency before using estimates for operational or reserves decisions.")
