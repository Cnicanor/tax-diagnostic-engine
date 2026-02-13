import unittest

from history_store import get_event_report_text


class HistoryStoreRealTests(unittest.TestCase):
    def test_rebuild_report_real_includes_componentes_pis_cofins(self) -> None:
        event_real = {
            "nome_empresa": "Empresa Real",
            "receita_anual": 1000000.0,
            "regime": "Lucro Real (estimado v1)",
            "detalhes_regime": {
                "regime_code": "REAL",
                "regime_model": "padrao",
                "margem_lucro_estimada": 0.10,
                "lucro_estimado": 100000.0,
                "irpj_calculado": 15000.0,
                "csll_calculado": 9000.0,
                "base_pis_cofins_usada": "receita_base_periodo",
                "valor_base_pis_cofins": 1000000.0,
                "debito_pis_cofins_nao_cumulativo": 92500.0,
                "credito_limitado_ao_debito": True,
                "credito_pis_cofins_original": 120000.0,
                "credito_pis_cofins_utilizado": 92500.0,
                "credito_pis_cofins": 0.0,
                "pis_cofins_nao_cumulativo_liquido": 0.0,
                "criterio_credito_pis_cofins": "nao_informado_assumido_zero",
            },
            "imposto_atual": 116500.0,
            "resultados": [],
        }

        report_text = get_event_report_text(event_real)
        self.assertIn("Regime atual: Lucro Real", report_text)
        self.assertIn("Base PIS/COFINS usada: Receita base do período", report_text)
        self.assertIn("Débito PIS/COFINS", report_text)
        self.assertIn("Crédito PIS/COFINS original", report_text)
        self.assertIn("Crédito PIS/COFINS utilizado", report_text)
        self.assertIn("Critério de crédito", report_text)
        self.assertNotIn("Detalhes do regime: {", report_text)
        self.assertNotIn("'regime_code':", report_text)
        self.assertNotIn("'ruleset_id':", report_text)


if __name__ == "__main__":
    unittest.main()
