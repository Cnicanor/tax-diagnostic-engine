import unittest

from company_profile import normalize_company_profile
from dto import DiagnosticInput
from recommendation_engine import build_recommendation


class RecommendationStrategicTests(unittest.TestCase):
    def test_ranking_inclui_warning(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa S1",
                receita_anual=1_000_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.12,
                modo_analise="estrategico",
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "OK",
                    "imposto_total": 120000.0,
                    "carga_efetiva_percentual": 12.0,
                    "alerts": [],
                    "critical_alerts": [],
                    "detalhes_regime": {},
                },
                {
                    "regime_code": "PRESUMIDO",
                    "regime_display": "Lucro Presumido",
                    "eligibility_status": "WARNING",
                    "imposto_total": 100000.0,
                    "carga_efetiva_percentual": 10.0,
                    "alerts": ["Tipo de atividade nao informado."],
                    "critical_alerts": [],
                    "detalhes_regime": {},
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        self.assertEqual(rec.get("modo"), "estrategico")
        self.assertEqual(rec.get("status"), "CONDICIONAL")
        ranking = rec.get("ranking", [])
        self.assertEqual(len(ranking), 2)
        self.assertTrue(any(item.get("status_elegibilidade") == "WARNING" for item in ranking))

    def test_blocked_fica_fora_do_ranking(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa S2",
                receita_anual=1_000_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.12,
                modo_analise="estrategico",
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "BLOCKED",
                    "imposto_total": None,
                    "carga_efetiva_percentual": None,
                    "alerts": ["Anexo do Simples nao informado."],
                    "critical_alerts": ["Anexo do Simples nao informado."],
                    "detalhes_regime": {},
                },
                {
                    "regime_code": "REAL",
                    "regime_display": "Lucro Real",
                    "eligibility_status": "OK",
                    "imposto_total": 110000.0,
                    "carga_efetiva_percentual": 11.0,
                    "alerts": [],
                    "critical_alerts": [],
                    "detalhes_regime": {},
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        ranking = rec.get("ranking", [])
        self.assertEqual(len(ranking), 1)
        self.assertEqual(ranking[0].get("regime_code"), "REAL")
        excluded = rec.get("excluded_regimes", [])
        self.assertTrue(any(item.get("regime") == "Simples Nacional" for item in excluded))

    def test_inconclusiva_quando_todos_blocked_ou_criticos(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa S3",
                receita_anual=1_000_000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                modo_analise="estrategico",
            )
        )
        comparison = {
            "rows": [
                {
                    "regime_code": "SIMPLES",
                    "regime_display": "Simples Nacional",
                    "eligibility_status": "BLOCKED",
                    "imposto_total": None,
                    "carga_efetiva_percentual": None,
                    "alerts": ["Anexo do Simples nao informado."],
                    "critical_alerts": ["Anexo do Simples nao informado."],
                    "detalhes_regime": {},
                },
                {
                    "regime_code": "PRESUMIDO",
                    "regime_display": "Lucro Presumido",
                    "eligibility_status": "BLOCKED",
                    "imposto_total": None,
                    "carga_efetiva_percentual": None,
                    "alerts": ["Receita anual acima do limite."],
                    "critical_alerts": ["Receita anual acima do limite."],
                    "detalhes_regime": {},
                },
            ]
        }
        rec = build_recommendation(profile, comparison)
        self.assertEqual(rec.get("status"), "INCONCLUSIVA")
        self.assertEqual(rec.get("ranking"), [])


if __name__ == "__main__":
    unittest.main()
