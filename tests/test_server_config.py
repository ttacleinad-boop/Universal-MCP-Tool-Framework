from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ServerConfigurationTests(unittest.TestCase):
    def test_environment_selected_config_controls_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "framework.json"
            path.write_text(
                json.dumps({"enabled_modes": ["read", "write"]}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"UNIVERSAL_MCP_CONFIG": str(path)}):
                sys.modules.pop("universal_mcp.server", None)
                module = importlib.import_module("universal_mcp.server")
                self.assertEqual(
                    sorted(mode.value for mode in module.runtime.config.enabled_modes),
                    ["read", "write"],
                )
        sys.modules.pop("universal_mcp.server", None)
        importlib.import_module("universal_mcp.server")


if __name__ == "__main__":
    unittest.main()
