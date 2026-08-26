from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_mcp.config import FrameworkConfig, load_config
from universal_mcp.examples import register_example_tools
from universal_mcp.models import ExecutionContext, OperationMode
from universal_mcp.registry import ToolRegistry
from universal_mcp.runtime import ToolRuntime


class ToolFrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        register_example_tools(self.registry)
        self.runtime = ToolRuntime(self.registry, FrameworkConfig())

    def test_discovery_reports_all_operation_modes(self) -> None:
        tools = {tool["name"]: tool for tool in self.registry.discover()}
        self.assertEqual(tools["example_get_time"]["mode"], "read")
        self.assertEqual(tools["example_write_note"]["mode"], "write")
        self.assertEqual(tools["example_run_check"]["mode"], "execute")

    def test_read_mode_is_available_by_default(self) -> None:
        result = self.runtime.execute("example_get_time")
        self.assertTrue(result.ok)
        self.assertIn("utc", result.data)

    def test_write_mode_is_denied_by_default(self) -> None:
        result = self.runtime.execute(
            "example_write_note",
            {"note": "hello"},
            ExecutionContext(scopes=frozenset({"notes:write"})),
        )
        self.assertFalse(result.ok)
        assert result.error is not None
        self.assertEqual(result.error["code"], "permission_denied")

    def test_execute_mode_requires_mode_and_scope(self) -> None:
        config = FrameworkConfig(
            enabled_modes=frozenset({OperationMode.READ, OperationMode.EXECUTE})
        )
        runtime = ToolRuntime(self.registry, config)
        denied = runtime.execute("example_run_check", {"target": "unit"})
        assert denied.error is not None
        self.assertEqual(denied.error["code"], "permission_denied")

        allowed = runtime.execute(
            "example_run_check",
            {"target": "unit"},
            ExecutionContext(scopes=frozenset({"checks:execute"})),
        )
        self.assertTrue(allowed.ok)
        self.assertEqual(allowed.data["status"], "simulated_pass")

    def test_unknown_tool_returns_structured_error(self) -> None:
        result = self.runtime.execute("not_registered")
        self.assertFalse(result.ok)
        assert result.error is not None
        self.assertEqual(result.error["code"], "tool_not_found")

    def test_status_is_machine_readable(self) -> None:
        status = self.runtime.status()
        self.assertEqual(status["tool_count"], 3)
        self.assertEqual(status["enabled_modes"], ["read"])

    def test_json_configuration_enables_explicit_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"enabled_modes": ["read", "write"], "log_level": "debug"}),
                encoding="utf-8",
            )
            config = load_config(path)
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(
            config.enabled_modes,
            frozenset({OperationMode.READ, OperationMode.WRITE}),
        )


if __name__ == "__main__":
    unittest.main()
