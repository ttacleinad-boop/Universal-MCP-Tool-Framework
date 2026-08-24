from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_mcp.scaffold import ScaffoldError, scaffold_project, validate_project


class ProjectScaffoldTests(unittest.TestCase):
    def test_python_library_scaffold_is_runnable_and_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample-library"
            result = scaffold_project(
                "Sample Library",
                root,
                project_type="python-library",
                initialize_git=True,
                install_dependencies=False,
            )
            self.assertTrue(result.git_initialized)
            self.assertFalse(result.dependencies_installed)
            self.assertTrue(result.validation["runnable"])
            self.assertTrue((root / ".git").is_dir())
            self.assertTrue((root / "src" / "sample_library" / "__init__.py").is_file())
            self.assertTrue((root / "config" / "development.json").is_file())
            self.assertTrue((root / "scripts" / "setup.sh").is_file())

            state = json.loads((root / ".project-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["project_type"], "python-library")
            self.assertTrue(state["git_initialized"])
            self.assertEqual(state["validation_state"], "pass")

    def test_mcp_tool_template_includes_standard_server_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample-mcp"
            result = scaffold_project(
                "Sample MCP",
                root,
                project_type="mcp-tool",
                initialize_git=False,
                install_dependencies=False,
            )
            self.assertTrue(result.validation["runnable"])
            self.assertTrue((root / "server.py").is_file())
            self.assertTrue((root / "src" / "sample_mcp" / "server.py").is_file())
            self.assertIn("mcp==2.0.0", (root / "pyproject.toml").read_text(encoding="utf-8"))

    def test_existing_nonempty_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "occupied"
            root.mkdir()
            (root / "existing.txt").write_text("occupied", encoding="utf-8")
            with self.assertRaises(ScaffoldError):
                scaffold_project(
                    "Blocked",
                    root,
                    initialize_git=False,
                    install_dependencies=False,
                )

    def test_missing_structure_reports_nonrunnable_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = validate_project(directory)
            self.assertFalse(result["runnable"])
            self.assertTrue(any(not check["passed"] for check in result["checks"]))


if __name__ == "__main__":
    unittest.main()
