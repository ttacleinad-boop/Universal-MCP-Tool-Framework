from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from universal_mcp.quality import format_markdown, run_quality_checks
from universal_mcp.scaffold import scaffold_project


class QualityToolkitTests(unittest.TestCase):
    def test_scaffolded_project_reports_expected_warning_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "quality-target"
            scaffold_project(
                "Quality Target",
                root,
                initialize_git=False,
                install_dependencies=False,
            )
            report = run_quality_checks(root)
            statuses = {check["name"]: check["status"] for check in report["checks"]}
            self.assertEqual(report["overall_status"], "WARNING")
            self.assertEqual(statuses["static_analysis"], "PASS")
            self.assertEqual(statuses["test_execution"], "PASS")
            self.assertEqual(statuses["build_verification"], "PASS")
            self.assertEqual(statuses["dependency_analysis"], "WARNING")
            self.assertEqual(statuses["regression_diff"], "WARNING")

    def test_invalid_python_source_fails_static_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            report = run_quality_checks(root)
            static = next(check for check in report["checks"] if check["name"] == "static_analysis")
            self.assertEqual(report["overall_status"], "FAIL")
            self.assertEqual(static["status"], "FAIL")

    def test_invalid_json_configuration_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "bad.json").write_text("{broken", encoding="utf-8")
            report = run_quality_checks(root)
            config = next(check for check in report["checks"] if check["name"] == "configuration_validation")
            self.assertEqual(config["status"], "FAIL")

    def test_markdown_report_preserves_statuses(self) -> None:
        report = {
            "overall_status": "WARNING",
            "checks": [
                {"name": "example", "status": "WARNING", "summary": "Example warning", "details": ""}
            ],
        }
        markdown = format_markdown(report)
        self.assertIn("**Overall:** WARNING", markdown)
        self.assertIn("| example | WARNING | Example warning |", markdown)


if __name__ == "__main__":
    unittest.main()
