import os
import unittest
from unittest.mock import patch

from demo_config import resolve_demo_mode, resolve_storage_targets


class DemoConfigTests(unittest.TestCase):
    def test_resolve_storage_targets_demo(self) -> None:
        targets = resolve_storage_targets(demo_mode=True)
        self.assertEqual(targets["history_pasta"], "data_demo")
        self.assertEqual(targets["history_arquivo"], "history.jsonl")
        self.assertEqual(targets["outputs_txt_pasta"], "outputs_demo")
        self.assertEqual(targets["outputs_pdf_pasta"], "outputs_demo_pdfs")

    def test_resolve_demo_mode_por_env_ou_toggle(self) -> None:
        with patch.dict(os.environ, {"TDE_DEMO": "1"}, clear=False):
            self.assertTrue(resolve_demo_mode(toggle_enabled=False))

        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(resolve_demo_mode(toggle_enabled=True))
            self.assertFalse(resolve_demo_mode(toggle_enabled=False))


if __name__ == "__main__":
    unittest.main()
