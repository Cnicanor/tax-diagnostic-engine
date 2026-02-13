import unittest

from dto import DiagnosticInput
from tax_engine import DiagnosticService


class PeriodicidadeMetadataTests(unittest.TestCase):
    def test_service_run_sets_periodicidade_default(self) -> None:
        service = DiagnosticService()
        inp = DiagnosticInput(
            nome_empresa="Empresa Default",
            receita_anual=100000.0,
            regime="Lucro Presumido",
            regime_code="PRESUMIDO",
            regime_model="padrao",
            tipo_atividade="Comercio",
        )

        out = service.run(inp)

        self.assertEqual(out.detalhes_regime.get("periodicidade"), "anual")
        self.assertEqual(out.detalhes_regime.get("competencia"), "Nao informada")
        self.assertIn("audit", out.detalhes_regime)

    def test_service_run_accepts_periodicidade_and_competencia(self) -> None:
        service = DiagnosticService()
        inp = DiagnosticInput(
            nome_empresa="Empresa Mensal",
            receita_anual=100000.0,
            regime="Lucro Presumido",
            regime_code="PRESUMIDO",
            regime_model="padrao",
            tipo_atividade="Servicos (geral)",
            periodicidade="mensal",
            competencia="2026-02",
        )

        out = service.run(inp)

        self.assertEqual(out.detalhes_regime.get("periodicidade"), "mensal")
        self.assertEqual(out.detalhes_regime.get("competencia"), "2026-02")


if __name__ == "__main__":
    unittest.main()
