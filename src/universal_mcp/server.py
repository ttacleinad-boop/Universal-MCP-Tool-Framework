from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server import MCPServer

from .config import FrameworkConfig, load_config
from .examples import register_example_tools
from .models import ExecutionContext
from .registry import ToolRegistry
from .runtime import ToolRuntime


def build_runtime(config: FrameworkConfig | None = None) -> ToolRuntime:
    config = config or FrameworkConfig()
    logging.basicConfig(level=config.log_level)
    registry = ToolRegistry()
    register_example_tools(registry)
    return ToolRuntime(registry=registry, config=config)


runtime = build_runtime(load_config(os.environ.get("UNIVERSAL_MCP_CONFIG")))
mcp = MCPServer("Universal MCP Tool Framework")


@mcp.tool()
def framework_health() -> dict[str, Any]:
    """Return framework liveness and server identity."""
    return runtime.health()


@mcp.tool()
def framework_status() -> dict[str, Any]:
    """Return enabled operation modes and registered tool metadata."""
    return runtime.status()


@mcp.tool()
def framework_discover_tools() -> list[dict[str, Any]]:
    """List registered framework tools and their permission requirements."""
    return runtime.registry.discover()


@mcp.tool()
def example_get_time() -> dict[str, Any]:
    """Run the read-only example tool through the framework runtime."""
    return runtime.execute("example_get_time").as_dict()


@mcp.tool()
def example_write_note(note: str) -> dict[str, Any]:
    """Attempt the scoped write example; it is denied by default in read-only mode."""
    return runtime.execute(
        "example_write_note",
        {"note": note},
        ExecutionContext(scopes=frozenset({"notes:write"})),
    ).as_dict()


@mcp.tool()
def example_run_check(target: str) -> dict[str, Any]:
    """Attempt the scoped execute example; it is denied by default in read-only mode."""
    return runtime.execute(
        "example_run_check",
        {"target": target},
        ExecutionContext(scopes=frozenset({"checks:execute"})),
    ).as_dict()
