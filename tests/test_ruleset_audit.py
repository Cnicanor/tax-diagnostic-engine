import tempfile
import unittest
from unittest.mock import patch

from ruleset_loader import DEFAULT_RULESET_ID, get_simples_tables
from tools.ruleset_audit import (
    audit_ruleset,
    render_audit_report_text,
    validate_required_keys,
    validate_simples_tables,
    write_audit_report,
)


class RulesetAuditTests(unittest.TestCase):
    def test_audit_ruleset_default_pass_and_hashes(self) -> None:
        result = audit_ruleset(DEFAULT_RULESET_ID)
        self.assertEqual(result.get("overall_status"), "PASS")
        self.assertEqual(len(result.get("ruleset_hash_sha256", "")), 64)
        self.assertEqual(len(result.get("baseline_hash_sha256", "")), 64)

    def test_validate_simples_tables_detects_anchor_divergence(self) -> None:
        tables = get_simples_tables(DEFAULT_RULESET_ID)
        tables["anexos"]["III"][3]["aliquota_nominal"] = 0.161

        with patch("tools.ruleset_audit.get_simples_tables", return_value=tables):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        failures = [c for c in result.get("checks", []) if c.get("status") == "FAIL"]
        self.assertTrue(any("Sentinela Simples: Anexo III faixa 4" == c.get("name") for c in failures))

    def test_validate_simples_tables_detects_partilha_soma_invalida(self) -> None:
        tables = get_simples_tables(DEFAULT_RULESET_ID)
        tables["anexos"]["I"][0]["percentuais_partilha"]["IRPJ"] = 0.99

        checks = validate_simples_tables(tables)
        failures = [c for c in checks if c.status == "FAIL"]
        self.assertTrue(any("partilha soma 1.0" in c.name for c in failures))

    def test_validate_required_keys_detects_missing_key(self) -> None:
        checks = validate_required_keys({"irpj": 0.15}, "Real", ("irpj", "csll"))
        self.assertTrue(any(c.status == "FAIL" and "csll" in c.name for c in checks))

    def test_audit_ruleset_fail_when_real_pis_out_of_range(self) -> None:
        invalid_real = {
            "irpj": 0.15,
            "csll": 0.09,
            "pis_nao_cumulativo": 1.5,
            "cofins_nao_cumulativo": 0.076,
        }
        with patch("tools.ruleset_audit.get_real_params", return_value=invalid_real):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        failures = [c for c in result.get("checks", []) if c.get("status") == "FAIL"]
        self.assertTrue(any("Real: faixa valida para 'pis_nao_cumulativo'" == c.get("name") for c in failures))

    def test_write_audit_report_generates_file(self) -> None:
        result = audit_ruleset(DEFAULT_RULESET_ID)
        report_text = render_audit_report_text(result)
        self.assertIn("RULESET AUDIT REPORT", report_text)
        self.assertIn("Ruleset hash (SHA-256):", report_text)
        self.assertIn("Baseline hash (SHA-256):", report_text)

        with tempfile.TemporaryDirectory() as tmp:
            path = write_audit_report(result, output_dir=tmp)
            with open(path, "r", encoding="utf-8") as file:
                persisted = file.read()

        self.assertIn("Overall: PASS", persisted)
        self.assertIn("JSON diffs (baseline vs ruleset):", persisted)

    def test_audit_ruleset_fail_when_eligibility_rules_invalid(self) -> None:
        invalid_elig = {"simples": {}, "presumido": {}, "real": {"warnings": "texto"}}
        with patch("tools.ruleset_audit.get_eligibility_rules", return_value=invalid_elig):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        self.assertEqual(result.get("overall_status"), "FAIL")
        failures = [c for c in result.get("checks", []) if c.get("status") == "FAIL"]
        self.assertTrue(any("Eligibility Simples: rbt12_max válido" == c.get("name") for c in failures))

    def test_audit_ruleset_fail_when_regime_catalog_missing_required_code(self) -> None:
        invalid_catalog = {
            "regimes": [
                {
                    "regime_code": "SIMPLES",
                    "display_name": "Simples Nacional",
                    "enabled": True,
                    "requires_fields": [],
                    "notes": "ok",
                }
            ]
        }
        with patch("tools.ruleset_audit.get_regime_catalog", return_value=invalid_catalog):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        self.assertEqual(result.get("overall_status"), "FAIL")
        failures = [c for c in result.get("checks", []) if c.get("status") == "FAIL"]
        self.assertTrue(any("Regime catalog: codigos obrigatorios" == c.get("name") for c in failures))

    def test_audit_ruleset_fail_when_thresholds_not_increasing(self) -> None:
        invalid_thresholds = {
            "portes": [
                {"porte": "MEI", "ordem": 1, "limite_receita_anual": 81000.0},
                {"porte": "ME", "ordem": 2, "limite_receita_anual": 50000.0},
            ]
        }
        with patch("tools.ruleset_audit.get_thresholds", return_value=invalid_thresholds):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        self.assertEqual(result.get("overall_status"), "FAIL")
        failures = [c for c in result.get("checks", []) if c.get("status") == "FAIL"]
        self.assertTrue(any("Thresholds: limites crescentes por ordem" == c.get("name") for c in failures))


if __name__ == "__main__":
    unittest.main()
