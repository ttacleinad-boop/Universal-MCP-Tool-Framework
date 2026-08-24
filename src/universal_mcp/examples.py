from __future__ import annotations

from datetime import UTC, datetime

from .models import OperationMode
from .registry import ToolRegistry


def register_example_tools(registry: ToolRegistry) -> None:
    """Register safe examples for every operation mode without external side effects."""

    @registry.register(
        name="example_get_time",
        description="Return the current UTC time.",
        mode=OperationMode.READ,
    )
    def example_get_time() -> dict[str, str]:
        return {"utc": datetime.now(UTC).isoformat()}

    @registry.register(
        name="example_write_note",
        description="Demonstrate a write-capable tool without persisting data.",
        mode=OperationMode.WRITE,
        required_scopes={"notes:write"},
    )
    def example_write_note(note: str) -> dict[str, str]:
        return {"accepted_note": note, "persistence": "not_implemented"}

    @registry.register(
        name="example_run_check",
        description="Demonstrate an execute-capable health check without invoking a process.",
        mode=OperationMode.EXECUTE,
        required_scopes={"checks:execute"},
    )
    def example_run_check(target: str) -> dict[str, str]:
        return {"target": target, "status": "simulated_pass"}
