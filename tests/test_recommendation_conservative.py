import unittest

from company_profile import normalize_company_profile
from dto import DiagnosticInput
from recommendation_engine import build_recommendation
from tax_engine import DiagnosticService


class RecommendationConservativeTests(unittest.TestCase):
    def test_recomendacao_negada_quando_sem_candidatos_ok(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa N",
                receita_anual=1_000_000.0,
                regime="Lucro Presumido",
                regime_code="PRESUMIDO",
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "BLOCKED",
                    "imposto_total": None,
                    "alerts": ["Anexo do Simples nao informado."],
                    "critical_alerts": ["Anexo do Simples nao informado."],
                },
                {
                    "regime_code": "PRESUMIDO",
                    "regime_display": "Lucro Presumido",
                    "eligibility_status": "WARNING",
                    "imposto_total": 100000.0,
                    "alerts": ["Tipo de atividade nao informado."],
                    "critical_alerts": ["Tipo de atividade nao informado."],
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        self.assertEqual(rec.get("status"), "NEGADA")
        self.assertTrue(rec.get("faltantes"))
        self.assertEqual(rec.get("candidate_policy"), "OK_only")
        self.assertTrue(rec.get("excluded_regimes"))

    def test_recomendacao_escolhe_menor_imposto_entre_ok(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa O",
                receita_anual=1_000_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.1,
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "OK",
                    "imposto_total": 120000.0,
                    "alerts": [],
                    "critical_alerts": [],
                },
                {
                    "regime_code": "REAL",
                    "regime_display": "Lucro Real",
                    "eligibility_status": "OK",
                    "imposto_total": 110000.0,
                    "alerts": [],
                    "critical_alerts": [],
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        self.assertEqual(rec.get("status"), "RECOMENDADA")
        self.assertEqual(rec.get("regime_recomendado"), "REAL")
        self.assertEqual(rec.get("candidate_policy"), "OK_only")

    def test_warning_com_imposto_menor_fica_excluido_com_justificativa(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa C",
                receita_anual=1_000_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.1,
                modo_analise="conservador",
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "OK",
                    "imposto_total": 120000.0,
                    "alerts": [],
                    "critical_alerts": [],
                },
                {
                    "regime_code": "PRESUMIDO",
                    "regime_display": "Lucro Presumido",
                    "eligibility_status": "WARNING",
                    "imposto_total": 90000.0,
                    "alerts": ["Tipo de atividade nao informado."],
                    "critical_alerts": ["Tipo de atividade nao informado."],
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        self.assertEqual(rec.get("status"), "RECOMENDADA")
        self.assertEqual(rec.get("regime_recomendado"), "SIMPLES")
        motivos = " | ".join(rec.get("por_que_nao_outros", []))
        self.assertIn("excluido por politica conservadora", motivos.lower())

    def test_relatorio_run_exibe_recomendacao_negada_com_status(self) -> None:
        out = DiagnosticService().run(
            DiagnosticInput(
                nome_empresa="Empresa Negada Integrada",
                receita_anual=120_000_000.0,
                regime="Lucro Presumido",
                regime_code="PRESUMIDO",
                regime_model="padrao",
                periodicidade="anual",
                competencia="2026",
                modo_analise="conservador",
            )
        )
        self.assertIn("=== RECOMENDAÇÃO (MODO CONSERVADOR) ===", out.relatorio_texto)
        self.assertIn("Status: NEGADA", out.relatorio_texto)
        self.assertIn("apenas regimes com elegibilidade OK", out.relatorio_texto)


if __name__ == "__main__":
    unittest.main()
