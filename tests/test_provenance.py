from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

import evaluate  # noqa: E402


class ProvenanceTests(unittest.TestCase):
    def test_uncommitted_run_uses_stable_source_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src" / "module.py"
            source.parent.mkdir()
            source.write_text("value = 1\n", encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()

            with patch.object(evaluate.subprocess, "run", side_effect=FileNotFoundError):
                commit, fingerprint, status = evaluate.resolve_run_provenance(root, None)

            self.assertEqual(commit, "")
            self.assertEqual(status, "uncommitted")
            self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")

            (reports / "output.csv").write_text("mutable output\n", encoding="utf-8")
            with patch.object(evaluate.subprocess, "run", side_effect=FileNotFoundError):
                _, fingerprint_after_output, _ = evaluate.resolve_run_provenance(root, None)
            self.assertEqual(fingerprint_after_output, fingerprint)

            source.write_text("value = 2\n", encoding="utf-8")
            self.assertNotEqual(evaluate.source_fingerprint(root), fingerprint)


if __name__ == "__main__":
    unittest.main()
