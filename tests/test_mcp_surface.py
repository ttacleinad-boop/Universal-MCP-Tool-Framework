from __future__ import annotations

import unittest

from mcp import Client

from universal_mcp.server import mcp


class McpSurfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_framework_status_is_available_through_mcp(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("framework_status", {})
        self.assertEqual(result.structured_content["tool_count"], 3)
        self.assertEqual(result.structured_content["enabled_modes"], ["read"])

    async def test_discovery_is_available_through_mcp(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("framework_discover_tools", {})
        names = {tool["name"] for tool in result.structured_content["result"]}
        self.assertEqual(
            names,
            {"example_get_time", "example_write_note", "example_run_check"},
        )


if __name__ == "__main__":
    unittest.main()
