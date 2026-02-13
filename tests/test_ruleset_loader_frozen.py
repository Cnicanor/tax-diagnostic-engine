import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ruleset_loader


class RulesetLoaderFrozenTests(unittest.TestCase):
    def test_load_ruleset_resolve_meipass_when_frozen(self) -> None:
        ruleset_id = "TEST_FROZEN_RULESET"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            rs_dir = base / "rulesets" / ruleset_id
            rs_dir.mkdir(parents=True, exist_ok=True)

            metadata = {
                "ruleset_id": ruleset_id,
                "vigencia_inicio": "2026-01-01",
                "vigencia_fim": None,
                "descricao": "ruleset de teste frozen",
            }
            with open(rs_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False)

            ruleset_loader._CACHE.clear()
            with patch.object(ruleset_loader.sys, "frozen", True, create=True), patch.object(
                ruleset_loader.sys, "_MEIPASS", str(base), create=True
            ):
                loaded = ruleset_loader.load_ruleset(ruleset_id)

            self.assertEqual(loaded["ruleset_id"], ruleset_id)


if __name__ == "__main__":
    unittest.main()
