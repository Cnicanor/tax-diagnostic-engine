import unittest

from dto import DiagnosticInput
from regimes import imposto_lucro_presumido, presuncao_por_tipo_atividade
from ruleset_loader import DEFAULT_RULESET_ID, get_presumido_params
from tax_engine import DiagnosticService


class PresuncaoAtividadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.params = get_presumido_params(DEFAULT_RULESET_ID)
        self.percentuais = self.params["percentual_presuncao"]

    def test_mapeamento_presuncao_por_tipo_atividade(self) -> None:
        self.assertEqual(presuncao_por_tipo_atividade("Comercio", self.percentuais), 0.08)
        self.assertEqual(presuncao_por_tipo_atividade("Industria", self.percentuais), 0.08)
        self.assertEqual(presuncao_por_tipo_atividade("Servicos (geral)", self.percentuais), 0.32)
        self.assertEqual(presuncao_por_tipo_atividade("Outros", self.percentuais), 0.32)
        self.assertEqual(presuncao_por_tipo_atividade("Desconhecido", self.percentuais), 0.08)
        self.assertEqual(presuncao_por_tipo_atividade(None, self.percentuais), 0.08)

    def test_comercio_e_servicos_geram_impostos_diferentes(self) -> None:
        receita = 1_000_000.0
        limite_anual = float(self.params["limites_adicional_irpj"]["anual"])
        imposto_comercio = imposto_lucro_presumido(
            receita_anual=receita,
            pis=float(self.params["pis"]),
            cofins=float(self.params["cofins"]),
            percentual_presuncao=presuncao_por_tipo_atividade("Comercio", self.percentuais),
            limite_adicional_irpj=limite_anual,
            irpj=float(self.params["irpj"]),
            adicional_irpj=float(self.params["adicional_irpj"]),
            csll=float(self.params["csll"]),
        )
        imposto_servicos = imposto_lucro_presumido(
            receita_anual=receita,
            pis=float(self.params["pis"]),
            cofins=float(self.params["cofins"]),
            percentual_presuncao=presuncao_por_tipo_atividade("Servicos (geral)", self.percentuais),
            limite_adicional_irpj=limite_anual,
            irpj=float(self.params["irpj"]),
            adicional_irpj=float(self.params["adicional_irpj"]),
            csll=float(self.params["csll"]),
        )

        self.assertGreater(imposto_servicos, imposto_comercio)

    def test_service_usa_tipo_atividade_no_presumido(self) -> None:
        service = DiagnosticService()
        receita = 1_000_000.0
        inp_comercio = DiagnosticInput(
            nome_empresa="Empresa C",
            receita_anual=receita,
            regime="Lucro Presumido",
            regime_code="PRESUMIDO",
            regime_model="padrao",
            tipo_atividade="Comercio",
        )
        inp_servicos = DiagnosticInput(
            nome_empresa="Empresa S",
            receita_anual=receita,
            regime="Lucro Presumido",
            regime_code="PRESUMIDO",
            regime_model="padrao",
            tipo_atividade="Servicos (geral)",
        )

        out_comercio = service.run(inp_comercio)
        out_servicos = service.run(inp_servicos)

        self.assertGreater(out_servicos.imposto_atual, out_comercio.imposto_atual)
        self.assertEqual(out_comercio.detalhes_regime.get("percentual_presuncao"), 0.08)
        self.assertEqual(out_servicos.detalhes_regime.get("percentual_presuncao"), 0.32)
        self.assertNotIn("Detalhes do regime: {", out_comercio.relatorio_texto)
        self.assertNotIn("'regime_code':", out_comercio.relatorio_texto)
        self.assertNotIn("'ruleset_id':", out_comercio.relatorio_texto)


if __name__ == "__main__":
    unittest.main()
