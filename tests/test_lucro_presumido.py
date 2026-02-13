import unittest

from regimes import imposto_lucro_presumido
from ruleset_loader import DEFAULT_RULESET_ID, get_presumido_params


class LucroPresumidoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.params = get_presumido_params(DEFAULT_RULESET_ID)
        self.pis = float(self.params["pis"])
        self.cofins = float(self.params["cofins"])
        self.irpj = float(self.params["irpj"])
        self.adicional_irpj = float(self.params["adicional_irpj"])
        self.csll = float(self.params["csll"])
        self.percentual = float(self.params["percentual_presuncao"]["Comercio"])
        self.limites = self.params["limites_adicional_irpj"]

    def _calc(self, receita_anual: float, periodicidade: str) -> float:
        limite = float(self.limites[periodicidade])
        return imposto_lucro_presumido(
            receita_anual=receita_anual,
            pis=self.pis,
            cofins=self.cofins,
            percentual_presuncao=self.percentual,
            limite_adicional_irpj=limite,
            irpj=self.irpj,
            adicional_irpj=self.adicional_irpj,
            csll=self.csll,
        )

    def test_adicional_irpj_zero_quando_base_abaixo_limite(self) -> None:
        receita_anual = 1_000_000.0  # base presumida = 80.000
        valor = self._calc(receita_anual, "anual")

        base_presumida = receita_anual * self.percentual
        expected = (
            receita_anual * (self.pis + self.cofins)
            + (base_presumida * self.irpj)
            + (base_presumida * self.csll)
            + 0.0
        )
        self.assertAlmostEqual(valor, expected, places=2)

    def test_adicional_irpj_somente_sobre_excedente(self) -> None:
        receita_anual = 4_000_000.0
        valor = self._calc(receita_anual, "anual")

        base_presumida = receita_anual * self.percentual
        excedente = max(0.0, base_presumida - float(self.limites["anual"]))
        expected = (
            receita_anual * (self.pis + self.cofins)
            + (base_presumida * self.irpj)
            + (base_presumida * self.csll)
            + (excedente * self.adicional_irpj)
        )
        self.assertAlmostEqual(valor, expected, places=2)

    def test_adicional_irpj_periodicidade_mensal(self) -> None:
        receita_anual = 4_000_000.0
        valor = self._calc(receita_anual, "mensal")

        base_presumida = receita_anual * self.percentual
        excedente = max(0.0, base_presumida - float(self.limites["mensal"]))
        expected = (
            receita_anual * (self.pis + self.cofins)
            + (base_presumida * self.irpj)
            + (base_presumida * self.csll)
            + (excedente * self.adicional_irpj)
        )
        self.assertAlmostEqual(valor, expected, places=2)
        self.assertAlmostEqual(excedente * self.adicional_irpj, 30_000.0, places=2)

    def test_adicional_irpj_periodicidade_trimestral(self) -> None:
        receita_anual = 4_000_000.0
        valor = self._calc(receita_anual, "trimestral")

        base_presumida = receita_anual * self.percentual
        excedente = max(0.0, base_presumida - float(self.limites["trimestral"]))
        expected = (
            receita_anual * (self.pis + self.cofins)
            + (base_presumida * self.irpj)
            + (base_presumida * self.csll)
            + (excedente * self.adicional_irpj)
        )
        self.assertAlmostEqual(valor, expected, places=2)
        self.assertAlmostEqual(excedente * self.adicional_irpj, 26_000.0, places=2)


if __name__ == "__main__":
    unittest.main()
