import json
import os
import tempfile
import unittest
from typing import Any, Dict, List

from history_store import get_event_report_text, list_events, normalize_event


def _scenario_row(nome: str) -> Dict[str, Any]:
    return {
        "nome_cenario": nome,
        "aliquota_reforma": 0.25,
        "imposto_reforma": 25000.0,
        "diferenca": 15000.0,
        "impacto_percentual": 15.0,
        "classificacao": "Alto impacto",
        "recomendacao": "Revisao urgente.",
    }


class HistoryStoreTests(unittest.TestCase):
    def test_normalize_event_legacy_cenarios_populates_resultados(self) -> None:
        legacy_event = {
            "nome_empresa": "Empresa Legacy",
            "receita_anual": "100000",
            "regime": "Simples Nacional (v1)",
            "imposto_atual": "8500",
            "cenarios": [_scenario_row("Base (25%)")],
        }

        normalized = normalize_event(legacy_event)

        self.assertEqual(normalized["cenarios"], legacy_event["cenarios"])
        self.assertEqual(normalized["resultados"], legacy_event["cenarios"])
        self.assertEqual(normalized["receita_anual"], 100000.0)
        self.assertEqual(normalized["imposto_atual"], 8500.0)
        self.assertEqual(normalized["regime"], "Simples Nacional")
        self.assertEqual(normalized["detalhes_regime"].get("regime_code"), "SIMPLES")
        self.assertEqual(normalized["detalhes_regime"].get("regime_model"), "manual")
        self.assertEqual(normalized.get("regime_original"), "Simples Nacional (v1)")

    def test_normalize_event_keeps_new_schema(self) -> None:
        resultados: List[Dict[str, Any]] = [_scenario_row("Otimista (23%)")]
        new_event = {
            "timestamp": "2026-02-12T12:00:00",
            "nome_empresa": "Empresa Nova",
            "receita_anual": 200000.0,
            "regime": "Lucro Presumido (v1)",
            "detalhes_regime": {"modelo": "defaults"},
            "imposto_atual": 18000.0,
            "resultados": resultados,
            "relatorio_texto": "Relatório salvo",
        }

        normalized = normalize_event(new_event)

        self.assertEqual(normalized["resultados"], resultados)
        self.assertEqual(normalized["cenarios"], resultados)
        self.assertEqual(normalized["relatorio_texto"], "Relatório salvo")
        self.assertEqual(normalized["regime"], "Lucro Presumido")
        self.assertEqual(normalized["detalhes_regime"].get("regime_code"), "PRESUMIDO")

    def test_list_events_ignores_corrupted_jsonl_lines(self) -> None:
        valid_older = {
            "timestamp": "2026-02-12T10:00:00",
            "nome_empresa": "Empresa A",
            "receita_anual": 100000.0,
            "regime": "Simples Nacional (v1)",
            "imposto_atual": 8500.0,
            "resultados": [],
        }
        valid_newer = {
            "timestamp": "2026-02-12T11:00:00",
            "nome_empresa": "Empresa B",
            "receita_anual": 120000.0,
            "regime": "Lucro Presumido (v1)",
            "imposto_atual": 13000.0,
            "resultados": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            history_file = os.path.join(tmp_dir, "history.jsonl")
            with open(history_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(valid_older, ensure_ascii=False) + "\n")
                f.write("{invalid json line}\n")
                f.write(json.dumps(valid_newer, ensure_ascii=False) + "\n")

            events = list_events(limit=50, pasta=tmp_dir, arquivo="history.jsonl")

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["nome_empresa"], "Empresa B")
        self.assertEqual(events[1]["nome_empresa"], "Empresa A")
        self.assertEqual(events[1]["regime"], "Simples Nacional")

    def test_get_event_report_text_rebuilds_when_relatorio_missing(self) -> None:
        event_without_report = {
            "nome_empresa": "Empresa Sem Relatório",
            "receita_anual": 100000.0,
            "regime": "Simples Nacional (v1)",
            "detalhes_regime": {"aliquota_efetiva": 0.085},
            "imposto_atual": 8500.0,
            "resultados": [_scenario_row("Base (25%)")],
        }

        report_text = get_event_report_text(event_without_report)

        self.assertIsInstance(report_text, str)
        self.assertTrue(report_text.strip())
        self.assertIn("Empresa: Empresa Sem Relatório", report_text)
        self.assertIn("Regime atual: Simples Nacional", report_text)
        self.assertIn("Relatório gerado em: (não disponível — evento legado)", report_text)
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)

    def test_get_event_report_text_presumido_includes_premissas_and_auditoria(self) -> None:
        event_presumido = {
            "nome_empresa": "Empresa Presumido",
            "receita_anual": 300000.0,
            "regime": "Lucro Presumido (v1)",
            "detalhes_regime": {
                "tipo_atividade_considerado": "Nao informado",
                "percentual_presuncao": 0.32,
                "alerta_premissa": "fallback de tipo_atividade aplicado.",
                "periodicidade": "trimestral",
                "competencia": "2026-T1",
                "audit": {
                    "ruleset_id": "BR_TAX_V1",
                    "ruleset_metadata": {
                        "ruleset_id": "BR_TAX_V1",
                        "vigencia_inicio": "2026-01-01",
                        "vigencia_fim": None,
                        "descricao": "legacy",
                    },
                    "integrity": {
                        "status": "PASS",
                        "ruleset_hash": "abc",
                        "baseline_hash": "def",
                        "checked_files": ["simples_tables.json"],
                    },
                    "as_of_date": "2026-02-12",
                    "generated_at": "2026-02-12T14:30:05",
                    "calculo_tipo": "estimativa_parametrizada",
                    "sources": ["Fonte A"],
                    "references": ["Ref A"],
                    "assumptions": ["Premissa A"],
                    "limitations": ["Limitação A"],
                },
            },
            "imposto_atual": 50000.0,
            "resultados": [_scenario_row("Base (25%)")],
        }

        report_text = get_event_report_text(event_presumido)

        self.assertIn("Regime atual: Lucro Presumido", report_text)
        self.assertIn("Periodicidade considerada: trimestral", report_text)
        self.assertIn("Competência: 2026-T1", report_text)
        self.assertIn("Tipo de atividade considerado: Não informado", report_text)
        self.assertIn("Percentual de presunção: 32.00%", report_text)
        self.assertIn("=== AUDITORIA (BASE NORMATIVA & PREMISSAS) ===", report_text)
        self.assertIn("Integridade ruleset/baseline: PASS", report_text)
        self.assertIn("Relatório gerado em: 12/02/2026 14:30:05", report_text)
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)

    def test_get_event_report_text_includes_periodo_when_present(self) -> None:
        event_com_periodo = {
            "nome_empresa": "Empresa Período",
            "receita_anual": 150000.0,
            "regime": "Simples Nacional (v1)",
            "detalhes_regime": {
                "aliquota_efetiva": 0.085,
                "periodicidade": "mensal",
                "competencia": "2026-02",
            },
            "imposto_atual": 12750.0,
            "resultados": [_scenario_row("Base (25%)")],
        }

        report_text = get_event_report_text(event_com_periodo)

        self.assertIn("Regime atual: Simples Nacional", report_text)
        self.assertIn("Periodicidade considerada: mensal", report_text)
        self.assertIn("Competência: 2026-02", report_text)
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)


if __name__ == "__main__":
    unittest.main()
