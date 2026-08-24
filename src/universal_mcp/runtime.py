from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .config import FrameworkConfig
from .models import (
    ExecutionContext,
    FrameworkError,
    PermissionDeniedError,
    ToolExecutionError,
    ToolResult,
)
from .registry import ToolRegistry


class ToolRuntime:
    """Executes registered tools through one permission and error boundary."""

    def __init__(self, registry: ToolRegistry, config: FrameworkConfig) -> None:
        self.registry = registry
        self.config = config
        self.logger = logging.getLogger("universal_mcp")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": self.config.server_name,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "service": self.config.server_name,
            "enabled_modes": sorted(mode.value for mode in self.config.enabled_modes),
            "tool_count": len(self.registry.discover()),
            "tools": self.registry.discover(),
        }

    def execute(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        context: ExecutionContext | None = None,
    ) -> ToolResult:
        context = context or ExecutionContext()
        payload = payload or {}
        try:
            tool = self.registry.get(name)
            if tool.mode not in self.config.enabled_modes:
                raise PermissionDeniedError(
                    f"mode '{tool.mode.value}' is disabled for tool '{name}'"
                )
            missing_scopes = tool.required_scopes - context.scopes
            if missing_scopes:
                scopes = ", ".join(sorted(missing_scopes))
                raise PermissionDeniedError(
                    f"tool '{name}' requires missing scope(s): {scopes}"
                )

            self.logger.info(
                "tool_execute actor=%s correlation_id=%s tool=%s mode=%s",
                context.actor,
                context.correlation_id,
                name,
                tool.mode.value,
            )
            return ToolResult(ok=True, data=tool.handler(**payload))
        except FrameworkError as exc:
            self.logger.warning(
                "tool_rejected actor=%s correlation_id=%s tool=%s code=%s",
                context.actor,
                context.correlation_id,
                name,
                exc.code,
            )
            return ToolResult(ok=False, error=exc.as_dict())
        except Exception as exc:  # Boundary converts implementation failures to a safe envelope.
            self.logger.exception(
                "tool_failed actor=%s correlation_id=%s tool=%s",
                context.actor,
                context.correlation_id,
                name,
            )
            error = ToolExecutionError(f"tool '{name}' failed: {exc.__class__.__name__}")
            return ToolResult(ok=False, error=error.as_dict())
