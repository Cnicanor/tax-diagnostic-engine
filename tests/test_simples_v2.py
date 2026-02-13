import unittest

from regimes import (
    aliquota_efetiva_simples,
    escolher_faixa_por_rbt12,
    imposto_simples_tabelado,
)
from ruleset_loader import DEFAULT_RULESET_ID, get_simples_tables


class SimplesV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tabelas = get_simples_tables(DEFAULT_RULESET_ID)
        self.anexo_i = self.tabelas["anexos"]["I"]

    def test_selecao_faixa_por_rbt12_limites(self) -> None:
        _, _, faixa_1 = escolher_faixa_por_rbt12(self.anexo_i, 180_000.0)
        _, _, faixa_2 = escolher_faixa_por_rbt12(self.anexo_i, 180_000.01)

        self.assertEqual(faixa_1, 1)
        self.assertEqual(faixa_2, 2)

    def test_aliquota_efetiva_formula(self) -> None:
        efetiva = aliquota_efetiva_simples(rbt12=360_000.0, aliq_nom=0.073, pd=5_940.0)
        self.assertAlmostEqual(efetiva, 0.0565, places=6)

    def test_fator_r_define_anexo_iii_quando_maior_ou_igual_028(self) -> None:
        _, detalhes = imposto_simples_tabelado(
            receita_base=500_000.0,
            rbt12=500_000.0,
            anexo="III/V",
            tabelas=self.tabelas,
            fator_r=0.28,
        )
        self.assertEqual(detalhes.get("anexo_aplicado"), "III")

    def test_fator_r_define_anexo_v_quando_menor_028(self) -> None:
        _, detalhes = imposto_simples_tabelado(
            receita_base=500_000.0,
            rbt12=500_000.0,
            anexo="III/V",
            tabelas=self.tabelas,
            fator_r=0.279,
        )
        self.assertEqual(detalhes.get("anexo_aplicado"), "V")


if __name__ == "__main__":
    unittest.main()
