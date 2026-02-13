import unittest

from ruleset_loader import (
    get_baseline_eligibility_rules,
    get_baseline_presumido_params,
    get_baseline_regime_catalog,
    get_baseline_real_params,
    get_baseline_simples_tables,
    get_baseline_thresholds,
    get_eligibility_rules,
    get_presumido_params,
    get_regime_catalog,
    get_real_params,
    get_simples_tables,
    get_thresholds,
    load_ruleset,
)


class RulesetLoaderTests(unittest.TestCase):
    def test_load_ruleset_metadata(self) -> None:
        metadata = load_ruleset("BR_TAX_2026_V1")
        self.assertEqual(metadata.get("ruleset_id"), "BR_TAX_2026_V1")
        self.assertEqual(metadata.get("vigencia_inicio"), "2026-01-01")

    def test_presumido_params_limites(self) -> None:
        params = get_presumido_params("BR_TAX_2026_V1")
        limites = params.get("limites_adicional_irpj", {})
        self.assertEqual(limites.get("mensal"), 20000)
        self.assertEqual(limites.get("trimestral"), 60000)
        self.assertEqual(limites.get("anual"), 240000)

    def test_real_params_contains_pis_cofins(self) -> None:
        params = get_real_params("BR_TAX_2026_V1")
        self.assertIn("pis_nao_cumulativo", params)
        self.assertIn("cofins_nao_cumulativo", params)

    def test_simples_tables_contains_limite_elegibilidade(self) -> None:
        tables = get_simples_tables("BR_TAX_2026_V1")
        self.assertIn("limite_elegibilidade_simples", tables)
        self.assertEqual(tables.get("limite_elegibilidade_simples"), 4800000)
        self.assertIn("fator_r_limite", tables)
        self.assertEqual(tables.get("fator_r_limite"), 0.28)
        self.assertEqual(tables.get("partilha_percentual_base"), "decimal_0_1")

    def test_baselines_exist_and_match(self) -> None:
        self.assertEqual(
            get_baseline_simples_tables("BR_TAX_2026_V1"),
            get_simples_tables("BR_TAX_2026_V1"),
        )
        self.assertEqual(
            get_baseline_presumido_params("BR_TAX_2026_V1"),
            get_presumido_params("BR_TAX_2026_V1"),
        )
        self.assertEqual(
            get_baseline_real_params("BR_TAX_2026_V1"),
            get_real_params("BR_TAX_2026_V1"),
        )
        self.assertEqual(
            get_baseline_eligibility_rules("BR_TAX_2026_V1"),
            get_eligibility_rules("BR_TAX_2026_V1"),
        )
        self.assertEqual(
            get_baseline_regime_catalog("BR_TAX_2026_V1"),
            get_regime_catalog("BR_TAX_2026_V1"),
        )
        self.assertEqual(
            get_baseline_thresholds("BR_TAX_2026_V1"),
            get_thresholds("BR_TAX_2026_V1"),
        )

    def test_regime_catalog_and_thresholds_structure(self) -> None:
        catalog = get_regime_catalog("BR_TAX_2026_V1")
        self.assertIn("regimes", catalog)
        self.assertGreaterEqual(len(catalog.get("regimes", [])), 3)
        thresholds = get_thresholds("BR_TAX_2026_V1")
        self.assertIn("portes", thresholds)
        self.assertGreaterEqual(len(thresholds.get("portes", [])), 4)

    def test_ruleset_inexistente_gera_erro(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_ruleset("BR_TAX_INEXISTENTE")


if __name__ == "__main__":
    unittest.main()
