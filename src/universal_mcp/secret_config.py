"""Strict, value-safe environment configuration and secret injection policy."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

_ENVIRONMENTS = frozenset({"development", "testing", "production"})
_TARGETS = frozenset({"build", "deployment"})
_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class SecretConfigError(ValueError):
    """Raised when a configuration policy or injection request is invalid."""


@dataclass(frozen=True)
class EnvironmentPolicy:
    """Validated non-secret configuration and secret-name policy for one environment."""

    public: Mapping[str, str]
    secret_names: tuple[str, ...]
    allowed_targets: tuple[str, ...]

    @classmethod
    def from_mapping(cls, environment: str, raw: object) -> "EnvironmentPolicy":
        if not isinstance(raw, dict) or set(raw) != {"public", "secret_names", "allowed_targets"}:
            raise SecretConfigError(f"{environment} policy has unsupported or missing fields")

        public = raw["public"]
        if not isinstance(public, dict):
            raise SecretConfigError(f"{environment}.public must be an object")
        normalized_public: dict[str, str] = {}
        for name, value in public.items():
            if not isinstance(name, str) or _NAME.fullmatch(name) is None:
                raise SecretConfigError(f"{environment}.public contains an invalid name")
            if not isinstance(value, str):
                raise SecretConfigError(f"{environment}.public values must be strings")
            normalized_public[name] = value

        secret_names = raw["secret_names"]
        if not isinstance(secret_names, list) or any(not isinstance(name, str) or _NAME.fullmatch(name) is None for name in secret_names):
            raise SecretConfigError(f"{environment}.secret_names is invalid")
        if secret_names != sorted(set(secret_names)):
            raise SecretConfigError(f"{environment}.secret_names must be unique and sorted")
        if set(normalized_public) & set(secret_names):
            raise SecretConfigError(f"{environment} exposes a secret name as public configuration")

        allowed_targets = raw["allowed_targets"]
        if not isinstance(allowed_targets, list) or not allowed_targets or any(target not in _TARGETS for target in allowed_targets):
            raise SecretConfigError(f"{environment}.allowed_targets is invalid")
        if allowed_targets != sorted(set(allowed_targets)):
            raise SecretConfigError(f"{environment}.allowed_targets must be unique and sorted")

        return cls(
            public=MappingProxyType(normalized_public),
            secret_names=tuple(secret_names),
            allowed_targets=tuple(allowed_targets),
        )


@dataclass(frozen=True)
class SecretConfigManager:
    """Environment-scoped policy that injects only declared values into approved targets.

    Secret values are supplied by the caller at injection time. This class never reads
    process environment variables, files referenced by the policy, or an external store.
    It returns values only from an explicit, validated injection call and provides a
    redacted summary for reporting.
    """

    environments: Mapping[str, EnvironmentPolicy]

    @classmethod
    def from_mapping(cls, raw: object) -> "SecretConfigManager":
        if not isinstance(raw, dict) or set(raw) != {"environments"}:
            raise SecretConfigError("secret configuration has unsupported or missing fields")
        environments = raw["environments"]
        if not isinstance(environments, dict) or not environments:
            raise SecretConfigError("environments must be a non-empty object")
        unknown = set(environments) - _ENVIRONMENTS
        if unknown:
            raise SecretConfigError(f"unsupported environments: {sorted(unknown)}")
        policies = {
            environment: EnvironmentPolicy.from_mapping(environment, environments[environment])
            for environment in sorted(environments)
        }
        return cls(environments=MappingProxyType(policies))

    @classmethod
    def from_json(cls, path: str | Path) -> "SecretConfigManager":
        try:
            with Path(path).open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise SecretConfigError(f"cannot load secret configuration: {exc}") from exc
        return cls.from_mapping(raw)

    def inject(self, environment: str, target: str, secret_values: Mapping[str, str]) -> dict[str, str]:
        policy = self._policy(environment)
        if target not in policy.allowed_targets:
            raise SecretConfigError(f"target is not allowed for {environment}: {target}")
        if not isinstance(secret_values, Mapping):
            raise SecretConfigError("secret_values must be a mapping")
        supplied_names = set(secret_values)
        required_names = set(policy.secret_names)
        if supplied_names != required_names:
            missing = sorted(required_names - supplied_names)
            unknown = sorted(supplied_names - required_names)
            raise SecretConfigError(f"secret value names do not match policy; missing={missing}; unknown={unknown}")
        if any(not isinstance(name, str) or not isinstance(value, str) or not value for name, value in secret_values.items()):
            raise SecretConfigError("secret values must be non-empty strings with valid names")
        injected = dict(policy.public)
        injected.update(secret_values)
        return injected

    def redacted_status(self, environment: str, target: str) -> dict[str, object]:
        policy = self._policy(environment)
        if target not in policy.allowed_targets:
            raise SecretConfigError(f"target is not allowed for {environment}: {target}")
        return {
            "environment": environment,
            "target": target,
            "public_config_count": len(policy.public),
            "declared_secret_count": len(policy.secret_names),
            "allowed": True,
            "secret_values_exposed": False,
        }

    def _policy(self, environment: str) -> EnvironmentPolicy:
        try:
            return self.environments[environment]
        except KeyError as exc:
            raise SecretConfigError(f"unsupported environment: {environment}") from exc
