import unittest

from ruleset_loader import DEFAULT_RULESET_ID, get_simples_tables


class RulesetSimplesTablesTests(unittest.TestCase):
    def test_simples_tables_tem_anexos_i_a_v_com_6_faixas(self) -> None:
        tabelas = get_simples_tables(DEFAULT_RULESET_ID)
        self.assertEqual(tabelas.get("limite_elegibilidade_simples"), 4800000)
        self.assertEqual(tabelas.get("fator_r_limite"), 0.28)
        self.assertEqual(tabelas.get("partilha_percentual_base"), "decimal_0_1")
        anexos = tabelas.get("anexos", {})

        for anexo in ("I", "II", "III", "IV", "V"):
            self.assertIn(anexo, anexos)
            faixas = anexos[anexo]
            self.assertIsInstance(faixas, list)
            self.assertEqual(len(faixas), 6)
            for faixa in faixas:
                self.assertIn("limite_superior", faixa)
                self.assertIn("aliquota_nominal", faixa)
                self.assertIn("parcela_deduzir", faixa)
                self.assertIn("percentuais_partilha", faixa)


if __name__ == "__main__":
    unittest.main()
