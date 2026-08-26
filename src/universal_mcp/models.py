from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class OperationMode(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclass(frozen=True)
class ExecutionContext:
    actor: str = "anonymous"
    scopes: frozenset[str] = field(default_factory=frozenset)
    correlation_id: str = "local"


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    mode: OperationMode
    required_scopes: frozenset[str]
    handler: Callable[..., Any]

    def public_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "mode": self.mode.value,
            "required_scopes": sorted(self.required_scopes),
        }


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any = None
    error: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class FrameworkError(Exception):
    code = "framework_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ToolNotFoundError(FrameworkError):
    code = "tool_not_found"


class DuplicateToolError(FrameworkError):
    code = "duplicate_tool"


class PermissionDeniedError(FrameworkError):
    code = "permission_denied"


class ToolExecutionError(FrameworkError):
    code = "tool_execution_failed"
