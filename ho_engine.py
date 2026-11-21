"""Core calculations and Excel parsing for a Havlena-Odeh oil-reservoir dashboard."""
from __future__ import annotations

import re
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd

REQUIRED_DATA = ["p", "Np", "Gp", "Bo", "Bg", "Rs"]
REQUIRED_PARAMS = ["pi", "Boi", "Bgi", "Rsi", "Swc", "Cw", "Cf"]

COLUMN_ALIASES = {
    "p": [
        "p", "p_psi", "pressure", "reservoir_pressure", "average_reservoir_pressure",
        "average_reservoir_pressure_p", "average_reservoir_pressure_psi",
        "average reservoir pressure p (psi)", "average reservoir pressure (psi)",
        "reservoir pressure p psi",
    ],
    "Np": [
        "np", "np_stb", "cumulative_oil_produced", "cumulative_oil_produced_np",
        "cumulative_oil_produced_stb", "cumulative oil produced np (stb)",
        "cumulative oil produced (stb)", "oil_production_cumulative_stb",
    ],
    "Gp": [
        "gp", "gp_scf", "gp_mscf", "gp_mmscf", "cumulative_gas_produced",
        "cumulative_gas_produced_gp", "cumulative_gas_produced_scf",
        "cumulative gas produced gp (scf)", "cumulative gas produced (scf)",
        "cumulative gas produced (mscf)", "gas_production_cumulative_scf",
    ],
    "Bo": [
        "bo", "bo_rb_per_stb", "oil_fvf", "oil_formation_volume_factor",
        "oil_fvf_bo_rb_per_stb", "oil fvf bo (rb/stb)", "oil formation volume factor bo",
    ],
    "Bg": [
        "bg", "bg_rb_per_scf", "gas_fvf", "gas_formation_volume_factor",
        "gas_fvf_bg_rb_per_scf", "gas fvf bg (rb/scf)", "gas formation volume factor bg",
    ],
    "Rs": [
        "rs", "rs_scf_per_stb", "solution_gor", "solution_gas_oil_ratio",
        "solution_gor_rs_scf_per_stb", "solution gor rs (scf/stb)",
        "solution gas-oil ratio rs",
    ],
}

PARAM_ALIASES = {
    "pi": ["pi", "pi_psi", "initial_pressure_pi", "initial_reservoir_pressure", "initial reservoir pressure pi"],
    "Boi": ["boi", "boi_rb_per_stb", "initial_oil_fvf_boi", "initial_oil_formation_volume_factor", "initial oil fvf boi"],
    "Bgi": ["bgi", "bgi_rb_per_scf", "initial_gas_fvf_bgi", "initial_gas_formation_volume_factor", "initial gas fvf bgi"],
    "Rsi": ["rsi", "rsi_scf_per_stb", "initial_solution_gor_rsi", "initial_solution_gas_oil_ratio", "initial solution gor rsi"],
    "Swc": ["swc", "swc_fraction", "connate_water_saturation_swc", "connate water saturation swc"],
    "Cw": ["cw", "cw_per_psi", "water_compressibility_cw", "water compressibility cw"],
    "Cf": ["cf", "cf_per_psi", "formation_compressibility_cf", "formation compressibility cf", "rock_compressibility_cf"],
}


def normalize_label(value: Any) -> str:
    """Lowercase a label and remove punctuation, spaces, and unit separators."""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _alias_lookup(alias_map: Dict[str, list[str]]) -> Dict[str, str]:
    out = {}
    for canonical, aliases in alias_map.items():
        for alias in aliases + [canonical]:
            out[normalize_label(alias)] = canonical
    return out


DATA_LOOKUP = _alias_lookup(COLUMN_ALIASES)
PARAM_LOOKUP = _alias_lookup(PARAM_ALIASES)


def map_data_columns(frame: pd.DataFrame) -> Dict[str, str]:
    """Map canonical variables to columns found in a worksheet."""
    mapped: Dict[str, str] = {}
    for col in frame.columns:
        key = DATA_LOOKUP.get(normalize_label(col))
        if key and key not in mapped:
            mapped[key] = col
    return mapped


def read_input_workbook(file_obj) -> Tuple[pd.DataFrame, Dict[str, float], str, str]:
    """Read the production/PVT sheet and parameter key-value sheet from an Excel file.

    The most complete sheet containing the six required production columns is selected.
    Other worksheets are scanned for a two-column Parameter / Value table.
    """
    xls = pd.ExcelFile(file_obj)
    best = None
    best_sheet = ""
    best_count = -1
    for sheet_name in xls.sheet_names:
        frame = pd.read_excel(xls, sheet_name=sheet_name)
        mapping = map_data_columns(frame)
        count = len(mapping)
        if count > best_count:
            best, best_sheet, best_count = frame, sheet_name, count
        if count == len(REQUIRED_DATA):
            best, best_sheet, best_count = frame, sheet_name, count
            break
    if best is None or best_count < len(REQUIRED_DATA):
        found = list(map_data_columns(best).keys()) if best is not None else []
        missing = [x for x in REQUIRED_DATA if x not in found]
        raise ValueError(
            "Could not identify all six production/PVT columns. Missing: " + ", ".join(missing)
            + ". Use the provided template headers or rename your columns to p_psi, Np_STB, "
              "Gp_scf, Bo_rb_per_STB, Bg_rb_per_scf, and Rs_scf_per_STB."
        )

    mapping = map_data_columns(best)
    production = best[[mapping[k] for k in REQUIRED_DATA]].copy()
    production.columns = REQUIRED_DATA

    params: Dict[str, float] = {}
    param_sheet = ""
    for sheet_name in xls.sheet_names:
        if sheet_name == best_sheet:
            continue
        frame = pd.read_excel(xls, sheet_name=sheet_name)
        if frame.empty or frame.shape[1] < 2:
            continue
        # Prefer explicit Parameter/Value columns, otherwise read first two columns.
        col_norms = {normalize_label(c): c for c in frame.columns}
        key_col = next((col_norms[k] for k in ("parameter", "parameters", "name", "variable") if k in col_norms), frame.columns[0])
        val_col = next((col_norms[k] for k in ("value", "values", "parameter_value") if k in col_norms), frame.columns[1])
        for _, row in frame[[key_col, val_col]].iterrows():
            key = PARAM_LOOKUP.get(normalize_label(row[key_col]))
            if key is None:
                continue
            try:
                val = float(row[val_col])
            except (TypeError, ValueError):
                continue
            params[key] = val
        if len(params) == len(REQUIRED_PARAMS):
            param_sheet = sheet_name
            break
        if params:
            param_sheet = sheet_name
    missing_params = [k for k in REQUIRED_PARAMS if k not in params]
    if missing_params:
        raise ValueError(
            "Missing initial reservoir parameters: " + ", ".join(missing_params)
            + ". Add a second sheet with columns Parameter and Value, using the provided template keys."
        )
    return production, params, best_sheet, param_sheet


def validate_parameters(params: Dict[str, float]) -> None:
    missing = [k for k in REQUIRED_PARAMS if k not in params]
    if missing:
        raise ValueError("Missing parameters: " + ", ".join(missing))
    for key in ("pi", "Boi", "Bgi"):
        if not np.isfinite(params[key]) or params[key] <= 0:
            raise ValueError(f"{key} must be a positive number.")
    if not np.isfinite(params["Rsi"]) or params["Rsi"] < 0:
        raise ValueError("Rsi must be zero or greater.")
    if not 0 <= params["Swc"] < 1:
        raise ValueError("Swc must be in the range 0 <= Swc < 1.")
    for key in ("Cw", "Cf"):
        if not np.isfinite(params[key]) or params[key] < 0:
            raise ValueError(f"{key} must be zero or greater.")


def calculate_havlena_odeh(
    production: pd.DataFrame,
    params: Dict[str, float],
    gas_unit: str = "scf",
    include_compressibility: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Calculate H–O variables and perform ordinary least-squares straight-line fit.

    Regression variables (including the supplied rock/connate-water compressibility):
      Efw0 = Boi * [(Cw*Swc + Cf)/(1-Swc)] * (pi-p)
      x = (Eg + Efw0)/(Eo + Efw0)
      y = F/(Eo + Efw0) = N + (N*m)*x

    The full expansion term is Efw = (1+m)*Efw0, so this rearrangement keeps
    the transformed equation linear in N and Nm. Water influx and produced water
    are not included because the requested input columns do not supply them.
    """
    validate_parameters(params)
    scales = {"scf": 1.0, "Mscf": 1_000.0, "MMscf": 1_000_000.0}
    if gas_unit not in scales:
        raise ValueError("Gas unit must be scf, Mscf, or MMscf.")

    df = production.copy().reset_index(drop=True)
    for col in REQUIRED_DATA:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.insert(0, "Excel row", np.arange(2, len(df) + 2))
    df["Gp_scf_used"] = df["Gp"] * scales[gas_unit]

    pi, Boi, Bgi, Rsi = (params[k] for k in ("pi", "Boi", "Bgi", "Rsi"))
    Swc, Cw, Cf = (params[k] for k in ("Swc", "Cw", "Cf"))

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        df["Rp_scf_per_STB"] = df["Gp_scf_used"] / df["Np"]
        df["F_rb"] = df["Np"] * (df["Bo"] + (df["Rp_scf_per_STB"] - df["Rs"]) * df["Bg"])
        df["Eo_rb_per_STB"] = (df["Bo"] - Boi) + (Rsi - df["Rs"]) * df["Bg"]
        df["Eg_rb_per_STB"] = Boi * (df["Bg"] / Bgi - 1.0)
        df["Efw0_rb_per_STB"] = Boi * ((Cw * Swc + Cf) / (1.0 - Swc)) * (pi - df["p"])
        if not include_compressibility:
            df["Efw0_rb_per_STB"] = 0.0
        df["Expansion_denominator"] = df["Eo_rb_per_STB"] + df["Efw0_rb_per_STB"]
        df["HO_x"] = (df["Eg_rb_per_STB"] + df["Efw0_rb_per_STB"]) / df["Expansion_denominator"]
        df["HO_y"] = df["F_rb"] / df["Expansion_denominator"]

    numeric_cols = REQUIRED_DATA
    basic_valid = df[numeric_cols].notna().all(axis=1)
    physical_valid = (
        (df["p"] > 0) & (df["Np"] > 0) & (df["Gp_scf_used"] >= 0)
        & (df["Bo"] > 0) & (df["Bg"] > 0) & (df["Rs"] >= 0)
    )
    finite_valid = np.isfinite(df[["HO_x", "HO_y", "Expansion_denominator"]]).all(axis=1)
    positive_expansion = df["Expansion_denominator"] > 1e-12
    df["Included"] = basic_valid & physical_valid & finite_valid & positive_expansion
    reasons = []
    for i, row in df.iterrows():
        if not basic_valid.iloc[i]:
            reasons.append("Missing or non-numeric required input")
        elif not physical_valid.iloc[i]:
            reasons.append("Non-physical input (check pressure, production, or FVF/GOR)")
        elif not finite_valid.iloc[i]:
            reasons.append("Non-finite transformed value")
        elif not positive_expansion.iloc[i]:
            reasons.append("Eo + Efw0 must be positive; initial/zero-expansion rows are excluded")
        else:
            reasons.append("Included")
    df["Reason"] = reasons

    valid = df.loc[df["Included"]].copy()
    if len(valid) < 3:
        raise ValueError(
            f"Only {len(valid)} valid production rows remain. At least 3 valid, depleted-state rows "
            "are required for a meaningful straight-line fit. Exclude the initial state (Np = 0) "
            "and check the units and input columns."
        )
    x = valid["HO_x"].to_numpy(dtype=float)
    y = valid["HO_y"].to_numpy(dtype=float)
    if np.ptp(x) <= max(1e-12, abs(np.mean(x)) * 1e-10):
        raise ValueError("H–O x-values have essentially no spread; N and m cannot be separated reliably.")

    design = np.column_stack([np.ones_like(x), x])
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    y_pred = intercept + slope * x
    residual = y - y_pred
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    m = slope / intercept if abs(intercept) > 1e-20 else float("nan")
    G_scf = m * intercept * Boi / Bgi if np.isfinite(m) else float("nan")

    valid["Fitted_HO_y"] = y_pred
    valid["Residual"] = residual
    df = df.merge(valid[["Excel row", "Fitted_HO_y", "Residual"]], on="Excel row", how="left")

    warnings = []
    if intercept <= 0:
        warnings.append("The fitted intercept N is not positive; check the data, units, and model applicability.")
    if slope < 0:
        warnings.append("The fitted slope is negative, giving a negative gas-cap ratio m; this is not physically expected for a conventional gas-cap reservoir.")
    if r2 < 0.90:
        warnings.append("R² is below 0.90. Review PVT consistency, pressure averaging, data quality, and model assumptions.")
    if np.ptp(x) < 0.05 * max(1.0, abs(np.mean(x))):
        warnings.append("The H–O x-values span a narrow range; N and m may be sensitive to small measurement errors.")
    if (valid["p"] > pi).any():
        warnings.append("One or more average pressures exceed pi. Confirm pressure units and whether the reservoir has undergone pressure maintenance.")
    if len(df) > len(valid):
        warnings.append(f"{len(df) - len(valid)} row(s) were excluded. Check the Reason column in the calculation table.")

    summary = {
        "N_STB": float(intercept),
        "slope_Nm_STB": float(slope),
        "m": float(m),
        "G_scf": float(G_scf),
        "R2": float(r2),
        "n_valid": int(len(valid)),
        "n_total": int(len(df)),
        "warnings": warnings,
        "include_compressibility": bool(include_compressibility),
        "gas_unit_input": gas_unit,
        "gas_scale_to_scf": scales[gas_unit],
    }
    return df, summary
