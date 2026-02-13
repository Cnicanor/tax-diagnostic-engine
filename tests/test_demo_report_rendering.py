import unittest

from dto import DiagnosticInput
from tax_engine import DiagnosticService


class DemoReportRenderingTests(unittest.TestCase):
    def _assert_no_dump(self, report_text: str) -> None:
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)
        self.assertIn("=== PARÂMETROS DO CÁLCULO ===", report_text)

    def test_demo_example_simples_sem_dump(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="DEMO Simples",
                receita_anual=850000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                periodicidade="anual",
                competencia="2026",
                rbt12=900000.0,
                receita_base_periodo=850000.0,
                anexo_simples="III/V",
                fator_r=0.30,
            )
        )
        self._assert_no_dump(out.relatorio_texto)

    def test_demo_example_presumido_sem_dump(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="DEMO Presumido",
                receita_anual=1000000.0,
                regime="Lucro Presumido",
                regime_code="PRESUMIDO",
                regime_model="padrao",
                periodicidade="anual",
                competencia="2026",
                tipo_atividade="Servicos (geral)",
            )
        )
        self._assert_no_dump(out.relatorio_texto)

    def test_demo_example_real_sem_dump(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="DEMO Real",
                receita_anual=2000000.0,
                regime="Lucro Real",
                regime_code="REAL",
                regime_model="padrao",
                periodicidade="anual",
                competencia="2026",
                margem_lucro=0.12,
            )
        )
        self._assert_no_dump(out.relatorio_texto)


if __name__ == "__main__":
    unittest.main()
