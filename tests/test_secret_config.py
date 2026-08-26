from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from universal_mcp.secret_config import SecretConfigError, SecretConfigManager


def _policy() -> dict[str, object]:
    return {
        "environments": {
            "development": {
                "public": {"LOG_LEVEL": "DEBUG"},
                "secret_names": ["API_TOKEN"],
                "allowed_targets": ["build", "deployment"],
            },
            "testing": {
                "public": {"LOG_LEVEL": "INFO"},
                "secret_names": [],
                "allowed_targets": ["build"],
            },
        }
    }


class SecretConfigManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = SecretConfigManager.from_mapping(_policy())

    def test_injection_merges_public_and_declared_secret_values(self) -> None:
        injected = self.manager.inject("development", "build", {"API_TOKEN": "test-token"})
        self.assertEqual(injected, {"LOG_LEVEL": "DEBUG", "API_TOKEN": "test-token"})

    def test_deployment_requires_explicit_environment_allowlist(self) -> None:
        with self.assertRaisesRegex(SecretConfigError, "target is not allowed"):
            self.manager.inject("testing", "deployment", {})

    def test_missing_or_unknown_secret_names_fail_closed(self) -> None:
        with self.assertRaisesRegex(SecretConfigError, "do not match policy"):
            self.manager.inject("development", "build", {})
        with self.assertRaisesRegex(SecretConfigError, "do not match policy"):
            self.manager.inject("testing", "build", {"API_TOKEN": "unexpected"})

    def test_secret_values_must_be_non_empty_strings(self) -> None:
        with self.assertRaisesRegex(SecretConfigError, "non-empty strings"):
            self.manager.inject("development", "build", {"API_TOKEN": ""})

    def test_redacted_status_never_contains_secret_values_or_names(self) -> None:
        status = self.manager.redacted_status("development", "deployment")
        self.assertEqual(status["public_config_count"], 1)
        self.assertEqual(status["declared_secret_count"], 1)
        self.assertFalse(status["secret_values_exposed"])
        self.assertNotIn("API_TOKEN", json.dumps(status))

    def test_unknown_environment_fails_closed(self) -> None:
        with self.assertRaisesRegex(SecretConfigError, "unsupported environment"):
            self.manager.redacted_status("production", "deployment")

    def test_exact_policy_shape_is_required(self) -> None:
        invalid = _policy()
        invalid["unexpected"] = True
        with self.assertRaisesRegex(SecretConfigError, "unsupported or missing fields"):
            SecretConfigManager.from_mapping(invalid)

    def test_secret_names_cannot_be_public(self) -> None:
        invalid = _policy()
        environments = invalid["environments"]
        self.assertIsInstance(environments, dict)
        development = environments["development"]
        self.assertIsInstance(development, dict)
        development["public"] = {"API_TOKEN": "never-inline-secrets"}
        with self.assertRaisesRegex(SecretConfigError, "exposes a secret name"):
            SecretConfigManager.from_mapping(invalid)

    def test_json_loader_reads_only_policy_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret-policy.json"
            path.write_text(json.dumps(_policy()), encoding="utf-8")
            loaded = SecretConfigManager.from_json(path)
        self.assertEqual(loaded.redacted_status("testing", "build")["declared_secret_count"], 0)


if __name__ == "__main__":
    unittest.main()
