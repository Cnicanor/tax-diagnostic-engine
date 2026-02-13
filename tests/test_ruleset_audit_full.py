import copy
import tempfile
import unittest
from unittest.mock import patch

from ruleset_loader import DEFAULT_RULESET_ID, get_baseline_simples_tables
from tools.ruleset_audit import audit_ruleset, write_audit_report


class RulesetAuditFullTests(unittest.TestCase):
    def test_pass_quando_ruleset_igual_baseline(self) -> None:
        result = audit_ruleset(DEFAULT_RULESET_ID)
        self.assertEqual(result.get("overall_status"), "PASS")
        self.assertEqual(result.get("json_differences"), [])

    def test_fail_quando_baseline_diverge(self) -> None:
        baseline_mutado = get_baseline_simples_tables(DEFAULT_RULESET_ID)
        baseline_mutado = copy.deepcopy(baseline_mutado)
        baseline_mutado["anexos"]["III"][3]["aliquota_nominal"] = 0.999

        with patch("tools.ruleset_audit.get_baseline_simples_tables", return_value=baseline_mutado):
            result = audit_ruleset(DEFAULT_RULESET_ID)

        self.assertEqual(result.get("overall_status"), "FAIL")
        self.assertGreater(len(result.get("json_differences", [])), 0)
        self.assertTrue(
            any("$.simples_tables.json.anexos.III[3].aliquota_nominal" in d.get("path", "") for d in result["json_differences"])
        )

    def test_relatorio_txt_gerado(self) -> None:
        result = audit_ruleset(DEFAULT_RULESET_ID)
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = write_audit_report(result, output_dir=tmp_dir)
            with open(report_path, "r", encoding="utf-8") as f:
                txt = f.read()

        self.assertIn("RULESET AUDIT REPORT (FULL)", txt)
        self.assertIn("Overall: PASS", txt)


if __name__ == "__main__":
    unittest.main()
