import unittest

from report_formatters import (
    render_comparativo_section,
    render_detalhes_regime,
    render_eligibilidade_section,
    render_recomendacao_section,
)


class ReportFormattersTests(unittest.TestCase):
    def test_render_detalhes_regime_sem_dict_cru(self) -> None:
        txt = render_detalhes_regime(
            "REAL",
            {
                "regime_code": "REAL",
                "margem_lucro_estimada": 0.12,
                "irpj": 0.15,
                "csll": 0.09,
                "base_pis_cofins_usada": "receita_anual",
                "valor_base_pis_cofins": 2_000_000.0,
                "pis_nao_cumulativo": 0.0165,
                "cofins_nao_cumulativo": 0.076,
                "debito_pis_cofins_nao_cumulativo": 185_000.0,
                "credito_pis_cofins": 0.0,
                "criterio_credito_pis_cofins": "nao_informado_assumido_zero",
            },
        )
        self.assertIn("=== PARÂMETROS DO CÁLCULO ===", txt)
        self.assertNotIn("{", txt)
        self.assertNotIn("}", txt)
        self.assertNotIn("'regime_code':", txt)

    def test_render_sections_padrao_e_ptbr(self) -> None:
        elig = {"REAL": {"status": "OK", "reasons": [], "missing_inputs": []}}
        comp = [
            {
                "regime_display": "Lucro Real",
                "eligibility_status": "OK",
                "imposto_total": 100000.0,
                "carga_efetiva_percentual": 11.37,
                "alerts": [],
            }
        ]
        rec = {
            "modo": "conservador",
            "status": "RECOMENDADA",
            "candidate_policy": "OK_only",
            "regime_recomendado_display": "Lucro Real",
            "justificativa": ["ok"],
            "excluded_regimes": [{"regime": "Presumido", "status": "WARNING", "reason": "dados faltantes"}],
        }

        self.assertIn("=== ELEGIBILIDADE ===", render_eligibilidade_section(elig))
        comparativo_txt = render_comparativo_section(comp)
        self.assertIn("=== COMPARATIVO ENTRE REGIMES ===", comparativo_txt)
        self.assertIn("R$ 100.000,00", comparativo_txt)
        self.assertIn("11,37%", comparativo_txt)
        rec_txt = render_recomendacao_section(rec)
        self.assertIn("=== RECOMENDAÇÃO (MODO CONSERVADOR) ===", rec_txt)
        self.assertIn("apenas regimes com elegibilidade OK", rec_txt)
        self.assertNotIn("{", rec_txt)

    def test_render_recomendacao_estrategica_sem_dict_cru(self) -> None:
        rec = {
            "modo": "estrategico",
            "status": "CONDICIONAL",
            "ranking": [
                {
                    "regime_display": "Simples Nacional",
                    "status_elegibilidade": "OK",
                    "imposto_total": 102340.0,
                    "carga_efetiva": 11.37,
                    "score": 87.5,
                    "tradeoffs": ["ok"],
                }
            ],
            "excluded_regimes": [{"regime": "Lucro Presumido", "status": "BLOCKED", "reason": "limite"}],
            "next_steps": ["Informar tipo_atividade"],
        }
        txt = render_recomendacao_section(rec)
        self.assertIn("=== RECOMENDAÇÃO (MODO ESTRATÉGICO) ===", txt)
        self.assertIn("Top 3 do ranking:", txt)
        self.assertNotIn("{", txt)
        self.assertNotIn("}", txt)


if __name__ == "__main__":
    unittest.main()
