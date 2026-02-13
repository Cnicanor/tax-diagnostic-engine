import unittest

from company_profile import normalize_company_profile
from dto import DiagnosticInput
from eligibility_engine import evaluate_eligibility
from ruleset_loader import DEFAULT_RULESET_ID


class EligibilityEngineTests(unittest.TestCase):
    def test_simples_blocked_quando_rbt12_acima_limite(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa X",
                receita_anual=6_000_000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                anexo_simples="I",
                rbt12=6_000_000.0,
            )
        )
        result = evaluate_eligibility(profile, DEFAULT_RULESET_ID)
        self.assertEqual(result["SIMPLES"].status, "BLOCKED")
        self.assertTrue(any("RBT12 acima" in reason for reason in result["SIMPLES"].reasons))

    def test_presumido_warning_quando_tipo_atividade_ausente(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa Y",
                receita_anual=1_000_000.0,
                regime="Lucro Presumido",
                regime_code="PRESUMIDO",
            )
        )
        result = evaluate_eligibility(profile, DEFAULT_RULESET_ID)
        self.assertEqual(result["PRESUMIDO"].status, "WARNING")
        self.assertIn("Tipo de atividade", result["PRESUMIDO"].missing_inputs[0])

    def test_real_ok_ou_warning_conforme_perfil(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa Z",
                receita_anual=1_000_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.12,
            )
        )
        result = evaluate_eligibility(profile, DEFAULT_RULESET_ID)
        self.assertIn(result["REAL"].status, ("OK", "WARNING"))


if __name__ == "__main__":
    unittest.main()
