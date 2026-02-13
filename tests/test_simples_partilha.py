import copy
import unittest
from unittest.mock import patch

from dto import DiagnosticInput
from tax_engine import DiagnosticService


class SimplesPartilhaTests(unittest.TestCase):
    def test_partilha_soma_valores_igual_imposto_total(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="Empresa Partilha",
                receita_anual=850000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                rbt12=900000.0,
                receita_base_periodo=850000.0,
                anexo_simples="III/V",
                fator_r=0.30,
                periodicidade="anual",
                competencia="2026",
            )
        )
        detalhes = out.detalhes_regime
        breakdown = detalhes.get("breakdown_das", {})
        self.assertIsInstance(breakdown, dict)
        self.assertAlmostEqual(sum(float(v) for v in breakdown.values()), float(out.imposto_atual), places=6)
        self.assertNotIn("Detalhes do regime: {", out.relatorio_texto)
        self.assertNotIn("'regime_code':", out.relatorio_texto)
        self.assertNotIn("'ruleset_id':", out.relatorio_texto)

    def test_partilha_percentuais_soma_1(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="Empresa Partilha",
                receita_anual=500000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                rbt12=500000.0,
                receita_base_periodo=500000.0,
                anexo_simples="I",
                periodicidade="anual",
                competencia="2026",
            )
        )
        percentuais = out.detalhes_regime.get("breakdown_percentuais", {})
        self.assertIsInstance(percentuais, dict)
        self.assertAlmostEqual(sum(float(v) for v in percentuais.values()), 1.0, places=6)

    def test_fail_fast_quando_chave_obrigatoria_ausente_no_ruleset(self) -> None:
        service = DiagnosticService()
        inp = DiagnosticInput(
            nome_empresa="Empresa FF",
            receita_anual=600000.0,
            regime="Simples Nacional",
            regime_code="SIMPLES",
            regime_model="tabelado",
            rbt12=600000.0,
            receita_base_periodo=600000.0,
            anexo_simples="I",
            periodicidade="anual",
            competencia="2026",
        )

        bad_tables = {
            "anexos": {},
            "fator_r_limite": 0.28,
            # chave limite_elegibilidade_simples propositalmente ausente
        }
        with patch("tax_engine.get_simples_tables", return_value=copy.deepcopy(bad_tables)):
            with self.assertRaises(ValueError) as ctx:
                service.run(inp)

        msg = str(ctx.exception)
        self.assertIn("ruleset_id=", msg)
        self.assertIn("arquivo=simples_tables.json", msg)
        self.assertIn("chave=limite_elegibilidade_simples", msg)
        self.assertIn("regime=Simples Nacional", msg)
        self.assertIn("impacto=", msg)


if __name__ == "__main__":
    unittest.main()
