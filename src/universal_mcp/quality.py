from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    summary: str
    details: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status.value,
            "summary": self.summary,
            "details": self.details,
        }


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def _source_files(root: Path) -> list[Path]:
    ignored = {".git", ".venv", "__pycache__", "build", "dist"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in ignored for part in path.relative_to(root).parts)
    )


def static_analysis(root: Path) -> CheckResult:
    errors: list[str] = []
    files = _source_files(root)
    if not files:
        return CheckResult("static_analysis", CheckStatus.WARNING, "No Python files found")

    for path in files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")

    if errors:
        return CheckResult(
            "static_analysis",
            CheckStatus.FAIL,
            f"{len(errors)} source file(s) failed syntax analysis",
            "\n".join(errors),
        )
    return CheckResult("static_analysis", CheckStatus.PASS, f"{len(files)} Python file(s) parsed successfully")


def dependency_analysis(root: Path) -> CheckResult:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return CheckResult("dependency_analysis", CheckStatus.WARNING, "No pyproject.toml found")
    content = pyproject.read_text(encoding="utf-8")
    if "[project]" not in content or "requires-python" not in content:
        return CheckResult(
            "dependency_analysis",
            CheckStatus.FAIL,
            "pyproject.toml is missing required project metadata",
        )
    if (root / ".venv").is_dir():
        return CheckResult("dependency_analysis", CheckStatus.PASS, "Project metadata and .venv are present")
    return CheckResult(
        "dependency_analysis",
        CheckStatus.WARNING,
        "Project metadata is present but no .venv was found",
    )


def configuration_validation(root: Path) -> CheckResult:
    config_root = root / "config"
    if not config_root.is_dir():
        return CheckResult("configuration_validation", CheckStatus.WARNING, "No config directory found")
    files = sorted(config_root.rglob("*.json"))
    if not files:
        return CheckResult("configuration_validation", CheckStatus.WARNING, "No JSON configuration files found")

    errors: list[str] = []
    for path in files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(root)}: {exc.msg} line {exc.lineno}")
    if errors:
        return CheckResult(
            "configuration_validation",
            CheckStatus.FAIL,
            f"{len(errors)} configuration file(s) are invalid JSON",
            "\n".join(errors),
        )
    return CheckResult("configuration_validation", CheckStatus.PASS, f"{len(files)} JSON configuration file(s) validated")


def test_execution(root: Path) -> CheckResult:
    tests_root = root / "tests"
    tests = sorted(tests_root.rglob("test_*.py")) if tests_root.is_dir() else []
    if not tests:
        return CheckResult("test_execution", CheckStatus.WARNING, "No test files discovered")

    source_root = root / "src"
    env = {**os.environ, "PYTHONPATH": str(source_root)} if source_root.is_dir() else dict(os.environ)
    code, output = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=root,
        env=env,
    )
    if code != 0:
        return CheckResult("test_execution", CheckStatus.FAIL, "Automated tests failed", output)
    return CheckResult("test_execution", CheckStatus.PASS, f"{len(tests)} test file(s) passed", output)


def build_verification(root: Path) -> CheckResult:
    source_root = root / "src"
    if not source_root.is_dir():
        return CheckResult("build_verification", CheckStatus.WARNING, "No src directory found")
    code, output = _run([sys.executable, "-m", "compileall", "-q", "src"], cwd=root)
    if code != 0:
        return CheckResult("build_verification", CheckStatus.FAIL, "Source compilation failed", output)
    return CheckResult("build_verification", CheckStatus.PASS, "Source compilation passed")


def regression_report(root: Path) -> CheckResult:
    if not (root / ".git").exists() or shutil.which("git") is None:
        return CheckResult("regression_diff", CheckStatus.WARNING, "Git diff unavailable for this project")
    code, output = _run(["git", "status", "--short"], cwd=root)
    if code != 0:
        return CheckResult("regression_diff", CheckStatus.WARNING, "Git status could not be collected", output)
    if output:
        return CheckResult("regression_diff", CheckStatus.WARNING, "Uncommitted changes detected", output)
    return CheckResult("regression_diff", CheckStatus.PASS, "Working tree is clean")


def run_quality_checks(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    if not root.is_dir():
        report = [CheckResult("project_root", CheckStatus.FAIL, "Project root does not exist")]
    else:
        report = [
            static_analysis(root),
            dependency_analysis(root),
            configuration_validation(root),
            test_execution(root),
            build_verification(root),
            regression_report(root),
        ]

    statuses = {result.status for result in report}
    overall = (
        CheckStatus.FAIL
        if CheckStatus.FAIL in statuses
        else CheckStatus.WARNING
        if CheckStatus.WARNING in statuses
        else CheckStatus.PASS
    )
    counts = {status.value: sum(result.status == status for result in report) for status in CheckStatus}
    return {
        "project_root": str(root),
        "generated_utc": datetime.now(UTC).isoformat(),
        "overall_status": overall.value,
        "summary": counts,
        "checks": [result.as_dict() for result in report],
    }


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local Code Quality Report",
        "",
        f"**Overall:** {report['overall_status']}",
        "",
        "| Check | Status | Summary |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | {check['status']} | {check['summary']} |")
    details = [check for check in report["checks"] if check["details"]]
    if details:
        lines.extend(["", "## Details"])
        for check in details:
            lines.extend(["", f"### {check['name']}", "```text", check["details"], "```"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Code Analysis and Testing Toolkit")
    parser.add_argument("path", nargs="?", default=".", help="Project directory to inspect")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    report = run_quality_checks(args.path)
    print(json.dumps(report, indent=2) if args.format == "json" else format_markdown(report))
    if report["overall_status"] == CheckStatus.FAIL.value:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
