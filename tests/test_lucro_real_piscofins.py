import unittest
from dataclasses import replace
from unittest.mock import patch

from dto import DiagnosticInput
from tax_engine import DiagnosticService


class LucroRealPisCofinsTests(unittest.TestCase):
    def _input_base(self) -> DiagnosticInput:
        return DiagnosticInput(
            nome_empresa="Empresa Real",
            receita_anual=1_000_000.0,
            regime="Lucro Real",
            regime_code="REAL",
            regime_model="padrao",
            margem_lucro=0.10,
            receita_base_periodo=1_000_000.0,
            periodicidade="anual",
            competencia="2026",
        )

    def test_sem_creditos_assume_zero_e_registra_premissa(self) -> None:
        out = DiagnosticService().run(self._input_base())

        self.assertAlmostEqual(out.imposto_atual, 116_500.0, places=2)
        self.assertAlmostEqual(float(out.detalhes_regime.get("credito_pis_cofins", 0.0)), 0.0, places=6)
        assumptions = out.detalhes_regime.get("audit", {}).get("assumptions", [])
        self.assertTrue(any("assumidos como zero" in str(s) for s in assumptions))
        self.assertNotIn("Detalhes do regime: {", out.relatorio_texto)
        self.assertNotIn("'regime_code':", out.relatorio_texto)
        self.assertNotIn("'ruleset_id':", out.relatorio_texto)

    def test_com_despesas_creditaveis_reduz_imposto(self) -> None:
        inp = self._input_base()
        inp = replace(inp, despesas_creditaveis=200_000.0)
        out = DiagnosticService().run(inp)

        self.assertAlmostEqual(float(out.detalhes_regime.get("credito_pis_cofins", 0.0)), 18_500.0, places=2)
        self.assertAlmostEqual(out.imposto_atual, 98_000.0, places=2)

    def test_com_percentual_credito_estimado_aplica_credito(self) -> None:
        inp = self._input_base()
        inp = replace(inp, percentual_credito_estimado=0.20)
        out = DiagnosticService().run(inp)

        self.assertAlmostEqual(float(out.detalhes_regime.get("credito_pis_cofins", 0.0)), 18_500.0, places=2)
        self.assertAlmostEqual(out.imposto_atual, 98_000.0, places=2)

    def test_credito_maior_que_debito_e_limitado(self) -> None:
        inp = self._input_base()
        inp = replace(inp, despesas_creditaveis=2_000_000.0)
        out = DiagnosticService().run(inp)

        self.assertTrue(bool(out.detalhes_regime.get("credito_limitado_ao_debito", False)))
        self.assertAlmostEqual(float(out.detalhes_regime.get("credito_pis_cofins_original", 0.0)), 185_000.0, places=2)
        self.assertAlmostEqual(float(out.detalhes_regime.get("credito_pis_cofins_utilizado", 0.0)), 92_500.0, places=2)
        self.assertAlmostEqual(float(out.detalhes_regime.get("pis_cofins_nao_cumulativo_liquido", 0.0)), 0.0, places=2)
        self.assertAlmostEqual(out.imposto_atual, 24_000.0, places=2)
        alerts = out.detalhes_regime.get("audit", {}).get("alerts", [])
        self.assertTrue(any("Crédito de PIS/COFINS informado excede o débito" in str(s) for s in alerts))

    def test_percentual_credito_estimado_maior_que_um_lanca_erro(self) -> None:
        inp = replace(self._input_base(), percentual_credito_estimado=1.2)
        with self.assertRaises(ValueError) as ctx:
            DiagnosticService().run(inp)
        msg = str(ctx.exception)
        self.assertIn("regime=Lucro Real", msg)
        self.assertIn("percentual_credito_estimado", msg)

    def test_fail_fast_quando_key_real_params_ausente(self) -> None:
        inp = self._input_base()
        bad_params = {"irpj": 0.15, "csll": 0.09, "pis_nao_cumulativo": 0.0165}
        with patch("tax_engine.get_real_params", return_value=bad_params):
            with self.assertRaises(ValueError) as ctx:
                DiagnosticService().run(inp)

        msg = str(ctx.exception)
        self.assertIn("ruleset_id=", msg)
        self.assertIn("arquivo=real_params.json", msg)
        self.assertIn("chave=cofins_nao_cumulativo", msg)
        self.assertIn("regime=Lucro Real", msg)
        self.assertIn("impacto=", msg)


if __name__ == "__main__":
    unittest.main()
