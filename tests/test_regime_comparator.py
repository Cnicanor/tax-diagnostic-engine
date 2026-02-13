import unittest

from company_profile import normalize_company_profile
from dto import DiagnosticInput
from regime_comparator import compare_regimes
from ruleset_loader import DEFAULT_RULESET_ID


class RegimeComparatorTests(unittest.TestCase):
    def test_compare_regimes_retorna_tres_linhas(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa C",
                receita_anual=900_000.0,
                regime="Simples Nacional",
                regime_code="SIMPLES",
                regime_model="tabelado",
                anexo_simples="III/V",
                rbt12=900_000.0,
                receita_base_periodo=850_000.0,
                fator_r=0.30,
                tipo_atividade="Servicos (geral)",
                margem_lucro=0.12,
            )
        )
        result = compare_regimes(profile, DEFAULT_RULESET_ID)
        rows = result.get("rows", [])
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["regime_code"] for row in rows}, {"SIMPLES", "PRESUMIDO", "REAL"})

    def test_compare_regimes_marca_simples_blocked_sem_anexo(self) -> None:
        profile = normalize_company_profile(
            DiagnosticInput(
                nome_empresa="Empresa D",
                receita_anual=900_000.0,
                regime="Lucro Real",
                regime_code="REAL",
                margem_lucro=0.12,
            )
        )
        result = compare_regimes(profile, DEFAULT_RULESET_ID)
        simples_row = next(row for row in result["rows"] if row["regime_code"] == "SIMPLES")
        self.assertEqual(simples_row["eligibility_status"], "BLOCKED")
        self.assertIsNone(simples_row["imposto_total"])


if __name__ == "__main__":
    unittest.main()
