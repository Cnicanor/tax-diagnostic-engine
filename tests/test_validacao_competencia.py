import unittest

from input_utils import validar_competencia, validar_periodicidade


class ValidacaoCompetenciaTests(unittest.TestCase):
    def test_validar_periodicidade_default(self) -> None:
        self.assertEqual(validar_periodicidade("desconhecida"), "anual")

    def test_mensal_valido(self) -> None:
        ok, valor = validar_competencia("mensal", "2026-02")
        self.assertTrue(ok)
        self.assertEqual(valor, "2026-02")

    def test_mensal_invalido(self) -> None:
        ok, erro = validar_competencia("mensal", "2026-13")
        self.assertFalse(ok)
        self.assertIn("mensal", erro)

    def test_trimestral_valido(self) -> None:
        ok, valor = validar_competencia("trimestral", "2026-T3")
        self.assertTrue(ok)
        self.assertEqual(valor, "2026-T3")

    def test_trimestral_invalido(self) -> None:
        ok, erro = validar_competencia("trimestral", "2026-T5")
        self.assertFalse(ok)
        self.assertIn("trimestral", erro)

    def test_anual_valido(self) -> None:
        ok, valor = validar_competencia("anual", "2026")
        self.assertTrue(ok)
        self.assertEqual(valor, "2026")

    def test_anual_invalido(self) -> None:
        ok, erro = validar_competencia("anual", "2026-01")
        self.assertFalse(ok)
        self.assertIn("anual", erro)


if __name__ == "__main__":
    unittest.main()
