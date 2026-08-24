from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import DuplicateToolError, OperationMode, ToolDefinition, ToolNotFoundError


class ToolRegistry:
    """Owns tool registration and exposes a stable discovery surface."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        *,
        name: str,
        description: str,
        mode: OperationMode,
        required_scopes: set[str] | frozenset[str] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            if name in self._tools:
                raise DuplicateToolError(f"tool '{name}' is already registered")
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                mode=mode,
                required_scopes=frozenset(required_scopes or set()),
                handler=handler,
            )
            return handler

        return decorator

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"tool '{name}' is not registered") from exc

    def discover(self) -> list[dict[str, Any]]:
        return [self._tools[name].public_metadata() for name in sorted(self._tools)]
