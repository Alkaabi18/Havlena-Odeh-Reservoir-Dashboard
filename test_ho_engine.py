"""Deterministic regression test for the included synthetic Excel template."""
from pathlib import Path
import unittest

from ho_engine import read_input_workbook, calculate_havlena_odeh


class HavlenaOdehSampleTest(unittest.TestCase):
    def test_sample_recovers_known_parameters(self):
        path = Path(__file__).with_name("Havlena_Odeh_Input_Template.xlsx")
        with path.open("rb") as workbook:
            production, params, production_sheet, parameter_sheet = read_input_workbook(workbook)
        calc, result = calculate_havlena_odeh(
            production,
            params,
            gas_unit="scf",
            include_compressibility=True,
        )
        self.assertEqual(production_sheet, "Production_PVT")
        self.assertEqual(parameter_sheet, "Initial_Parameters")
        self.assertEqual(result["n_valid"], 6)
        self.assertAlmostEqual(result["N_STB"], 10_000_000, delta=1)
        self.assertAlmostEqual(result["m"], 0.25, places=8)
        self.assertAlmostEqual(result["G_scf"], 3_906_250_000, delta=10)
        self.assertAlmostEqual(result["R2"], 1.0, places=10)

    def test_classical_no_compressibility_regression_is_finite(self):
        path = Path(__file__).with_name("Havlena_Odeh_Input_Template.xlsx")
        with path.open("rb") as workbook:
            production, params, _, _ = read_input_workbook(workbook)
        _, result = calculate_havlena_odeh(
            production,
            params,
            gas_unit="scf",
            include_compressibility=False,
        )
        self.assertEqual(result["n_valid"], 6)
        self.assertTrue(result["N_STB"] > 0)
        self.assertTrue(result["G_scf"] > 0)
        self.assertTrue(0 < result["m"] < 2)

    def test_mscf_input_conversion_matches_scf(self):
        import pandas as pd
        path = Path(__file__).with_name("Havlena_Odeh_Input_Template.xlsx")
        with path.open("rb") as workbook:
            production, params, _, _ = read_input_workbook(workbook)
        production_mscf = production.copy()
        production_mscf["Gp"] = production_mscf["Gp"] / 1000.0
        _, result = calculate_havlena_odeh(
            production_mscf, params, gas_unit="Mscf", include_compressibility=True
        )
        self.assertAlmostEqual(result["N_STB"], 10_000_000, delta=1)
        self.assertAlmostEqual(result["m"], 0.25, places=8)
        self.assertAlmostEqual(result["G_scf"], 3_906_250_000, delta=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
