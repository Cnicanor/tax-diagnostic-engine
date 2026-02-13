import unittest

from history_store import build_refreshed_event, build_report_from_event, has_audit


class ReportRefreshTests(unittest.TestCase):
    def test_build_report_from_event_legado_sem_audit(self) -> None:
        legacy_event = {
            "nome_empresa": "Empresa Legado",
            "receita_anual": 100000.0,
            "regime": "Lucro Presumido (v1)",
            "detalhes_regime": {
                "tipo_atividade_considerado": "Servicos (geral)",
                "percentual_presuncao": 0.32,
            },
            "imposto_atual": 20000.0,
            "resultados": [],
            "relatorio_texto": "texto antigo",
        }

        report_text = build_report_from_event(legacy_event)

        self.assertNotIn("=== AUDITORIA (BASE NORMATIVA & PREMISSAS) ===", report_text)
        self.assertIn("Relatório gerado em: (não disponível — evento legado)", report_text)
        self.assertIn("Regime atual: Lucro Presumido", report_text)
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)

    def test_build_refreshed_event_inclui_audit_e_relatorio_novo(self) -> None:
        legacy_event = {
            "nome_empresa": "Empresa Legado",
            "receita_anual": 100000.0,
            "regime": "Simples Nacional (v1)",
            "detalhes_regime": {
                "aliquota_efetiva": 0.09,
                "periodicidade": "anual",
            },
            "imposto_atual": 9000.0,
            "resultados": [],
            "relatorio_texto": "texto antigo",
        }

        refreshed = build_refreshed_event(legacy_event)

        self.assertEqual(refreshed.get("evento_tipo"), "report_refresh")
        self.assertTrue(has_audit(refreshed))
        self.assertEqual(refreshed.get("regime"), "Simples Nacional")
        self.assertEqual(refreshed.get("detalhes_regime", {}).get("regime_model"), "manual")
        self.assertIn("legado/manual", refreshed.get("detalhes_regime", {}).get("origem_evento", ""))
        self.assertEqual(float(refreshed.get("imposto_atual", 0.0)), float(legacy_event.get("imposto_atual", 0.0)))

        texto = refreshed.get("relatorio_texto", "")
        self.assertIn("=== AUDITORIA (BASE NORMATIVA & PREMISSAS) ===", texto)
        self.assertIn("Relatório gerado em:", texto)
        self.assertNotIn("(não disponível — evento legado)", texto)
        self.assertIn("Origem do evento: legado/manual (migração).", texto)
        self.assertIn("partilha indisponível (evento legado)", texto)
        self.assertNotIn("Detalhes do regime: {", texto)
        self.assertNotIn("'regime_code':", texto)
        self.assertNotIn("'ruleset_id':", texto)

    def test_build_report_from_event_legado_simples_sem_partilha_mostra_indisponivel(self) -> None:
        legacy_event = {
            "nome_empresa": "Empresa Legado Simples",
            "receita_anual": 120000.0,
            "regime": "Simples Nacional (v1)",
            "detalhes_regime": {
                "aliquota_efetiva": 0.09,
                "periodicidade": "anual",
            },
            "imposto_atual": 10800.0,
            "resultados": [],
        }

        report_text = build_report_from_event(legacy_event)
        self.assertIn("=== SIMPLES NACIONAL — PARTILHA DO DAS (ESTIMATIVA) ===", report_text)
        self.assertIn("partilha indisponível (evento legado)", report_text)

    def test_refresh_legado_v2_reconstroi_partilha(self) -> None:
        legacy_event = {
            "nome_empresa": "Empresa Legado V2",
            "receita_anual": 500000.0,
            "regime": "Simples Nacional (v2 — tabelado)",
            "detalhes_regime": {
                "regime_code": "SIMPLES",
                "regime_model": "tabelado",
                "anexo_aplicado": "I",
                "faixa": 3,
                "periodicidade": "anual",
                "competencia": "2026",
            },
            "imposto_atual": 33640.0,
            "resultados": [],
            "relatorio_texto": "texto antigo",
        }

        refreshed = build_refreshed_event(legacy_event)
        detalhes = refreshed.get("detalhes_regime", {})
        self.assertIsInstance(detalhes.get("breakdown_percentuais"), dict)
        self.assertIsInstance(detalhes.get("breakdown_das"), dict)
        self.assertTrue(detalhes.get("partilha_reconstruida_no_refresh"))


if __name__ == "__main__":
    unittest.main()
