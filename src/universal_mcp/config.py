from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import OperationMode


@dataclass(frozen=True)
class FrameworkConfig:
    server_name: str = "Universal MCP Tool Framework"
    enabled_modes: frozenset[OperationMode] = field(
        default_factory=lambda: frozenset({OperationMode.READ})
    )
    log_level: str = "INFO"

    @classmethod
    def from_mapping(cls, raw: dict[str, object]) -> "FrameworkConfig":
        modes = raw.get("enabled_modes", [OperationMode.READ.value])
        if not isinstance(modes, list) or not all(isinstance(mode, str) for mode in modes):
            raise ValueError("enabled_modes must be a list of mode names")
        return cls(
            server_name=str(raw.get("server_name", cls.server_name)),
            enabled_modes=frozenset(OperationMode(mode) for mode in modes),
            log_level=str(raw.get("log_level", "INFO")).upper(),
        )


def load_config(path: str | Path | None = None) -> FrameworkConfig:
    if path is None:
        return FrameworkConfig()

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("framework configuration must be a JSON object")
    return FrameworkConfig.from_mapping(raw)
