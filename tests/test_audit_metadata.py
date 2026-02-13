import unittest

from dto import DiagnosticInput
from tax_engine import DiagnosticService


class AuditMetadataTests(unittest.TestCase):
    def test_run_includes_audit_metadata_and_report_block(self) -> None:
        service = DiagnosticService()
        out = service.run(
            DiagnosticInput(
                nome_empresa="Empresa Auditoria",
                receita_anual=500000.0,
                regime="Lucro Presumido",
                regime_code="PRESUMIDO",
                regime_model="padrao",
                tipo_atividade="Servicos (geral)",
            )
        )

        audit = out.detalhes_regime.get("audit")
        self.assertIsInstance(audit, dict)

        self.assertEqual(audit.get("ruleset_id"), "BR_TAX_2026_V1")
        self.assertTrue(audit.get("generated_at"))
        self.assertTrue(audit.get("calculo_tipo"))
        self.assertIsInstance(audit.get("ruleset_metadata"), dict)
        self.assertEqual(audit.get("ruleset_metadata", {}).get("ruleset_id"), "BR_TAX_2026_V1")
        self.assertIsInstance(audit.get("references"), list)
        self.assertGreater(len(audit.get("references", [])), 0)
        self.assertIsInstance(audit.get("integrity"), dict)
        self.assertEqual(audit.get("integrity", {}).get("status"), "PASS")

        self.assertIsInstance(audit.get("sources"), list)
        self.assertIsInstance(audit.get("assumptions"), list)
        self.assertIsInstance(audit.get("limitations"), list)
        self.assertGreater(len(audit.get("sources")), 0)
        self.assertGreater(len(audit.get("assumptions")), 0)
        self.assertGreater(len(audit.get("limitations")), 0)
        self.assertTrue(any("Adicional IRPJ" in s for s in audit.get("assumptions", [])))

        self.assertIn("=== AUDITORIA", out.relatorio_texto)
        self.assertIn("Relatorio gerado em:", out.relatorio_texto)


if __name__ == "__main__":
    unittest.main()
