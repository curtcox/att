"""Test execution utilities."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

type TestResultValue = str | int | float | bool
type TestResultPayload = dict[str, TestResultValue]

_SUMMARY_COUNT_PATTERN = re.compile(
    r"(?P<count>\d+)\s+(?P<label>passed|failed|skipped|error|errors|xfailed|xpassed)"
)
_SUMMARY_DURATION_PATTERN = re.compile(r"\bin\s+(?P<seconds>[0-9]*\.?[0-9]+)s\b")
_NO_TESTS_PATTERN = re.compile(r"\bno tests ran\b", re.IGNORECASE)
_TESTSUITE_TAG_PATTERN = re.compile(r"<testsuite\b(?P<attrs>[^>]*)>", re.IGNORECASE)
_XML_ATTR_PATTERN = re.compile(r'(?P<key>[A-Za-z_][A-Za-z0-9_]*)="(?P<value>[^"]*)"')


class PytestSummary(TypedDict):
    passed: int
    failed: int
    skipped: int
    errors: int
    xfailed: int
    xpassed: int
    duration_seconds: float | None
    no_tests_collected: bool


@dataclass(slots=True)
class RunResult:
    """Test run summary."""

    command: str
    returncode: int
    output: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    xfailed: int = 0
    xpassed: int = 0
    duration_seconds: float | None = None
    no_tests_collected: bool = False
    timed_out: bool = False

    def as_payload(self) -> TestResultPayload:
        """Return a transport-friendly result payload."""
        payload: TestResultPayload = {
            "command": self.command,
            "returncode": self.returncode,
            "output": self.output,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "xfailed": self.xfailed,
            "xpassed": self.xpassed,
            "no_tests_collected": self.no_tests_collected,
            "timed_out": self.timed_out,
        }
        if self.duration_seconds is not None:
            payload["duration_seconds"] = self.duration_seconds
        return payload


class TestRunner:
    """Execute tests in project context."""

    def run(
        self,
        project_path: Path,
        suite: str = "unit",
        *,
        markers: str | None = None,
        timeout_seconds: int | None = None,
    ) -> RunResult:
        suite_name = suite.strip()
        target = {
            "unit": "tests/unit",
            "integration": "tests/integration",
            "e2e": "tests/e2e",
            "property": "tests/property",
            "all": "tests",
        }.get(suite_name, suite_name or "tests")

        command = ["pytest", target]
        if markers is not None and markers.strip():
            command.extend(["-m", markers.strip()])

        timeout = timeout_seconds if timeout_seconds is not None and timeout_seconds > 0 else None

        command_text = " ".join(command)

        try:
            completed = subprocess.run(
                command,
                cwd=project_path,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            output = _coerce_text(exc.stdout) + _coerce_text(exc.stderr)
            summary = parse_pytest_output_summary(output)
            return RunResult(
                command=command_text,
                returncode=124,
                output=output,
                passed=summary["passed"],
                failed=summary["failed"],
                skipped=summary["skipped"],
                errors=summary["errors"],
                xfailed=summary["xfailed"],
                xpassed=summary["xpassed"],
                duration_seconds=summary["duration_seconds"],
                no_tests_collected=summary["no_tests_collected"],
                timed_out=True,
            )

        output = (completed.stdout or "") + (completed.stderr or "")
        summary = parse_pytest_output_summary(output)
        return RunResult(
            command=command_text,
            returncode=completed.returncode,
            output=output,
            passed=summary["passed"],
            failed=summary["failed"],
            skipped=summary["skipped"],
            errors=summary["errors"],
            xfailed=summary["xfailed"],
            xpassed=summary["xpassed"],
            duration_seconds=summary["duration_seconds"],
            no_tests_collected=summary["no_tests_collected"],
        )


def parse_pytest_output_summary(output: str) -> PytestSummary:
    """Parse count/duration summary from pytest console output."""
    summary: PytestSummary = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "xfailed": 0,
        "xpassed": 0,
        "duration_seconds": None,
        "no_tests_collected": False,
    }
    if not output:
        return summary

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    summary_line = ""
    for line in reversed(lines):
        if _NO_TESTS_PATTERN.search(line) or _SUMMARY_COUNT_PATTERN.search(line):
            summary_line = line
            break

    if summary_line:
        for match in _SUMMARY_COUNT_PATTERN.finditer(summary_line):
            count = int(match.group("count"))
            label = match.group("label")
            if label == "passed":
                summary["passed"] = count
            elif label == "failed":
                summary["failed"] = count
            elif label == "skipped":
                summary["skipped"] = count
            elif label in {"error", "errors"}:
                summary["errors"] = count
            elif label == "xfailed":
                summary["xfailed"] = count
            elif label == "xpassed":
                summary["xpassed"] = count

        duration_match = _SUMMARY_DURATION_PATTERN.search(summary_line)
        if duration_match:
            summary["duration_seconds"] = float(duration_match.group("seconds"))

        if _NO_TESTS_PATTERN.search(summary_line):
            summary["no_tests_collected"] = True

    return summary


def parse_pytest_json_report(content: str) -> PytestSummary:
    """Parse summary counts from a pytest-json-report payload."""
    parsed = json.loads(content)
    summary_data = parsed.get("summary", {}) if isinstance(parsed, dict) else {}
    total_collected = summary_data.get("collected")
    total = summary_data.get("total")

    return {
        "passed": int(summary_data.get("passed", 0) or 0),
        "failed": int(summary_data.get("failed", 0) or 0),
        "skipped": int(summary_data.get("skipped", 0) or 0),
        "errors": int(summary_data.get("error", summary_data.get("errors", 0)) or 0),
        "xfailed": int(summary_data.get("xfailed", 0) or 0),
        "xpassed": int(summary_data.get("xpassed", 0) or 0),
        "duration_seconds": float(parsed.get("duration")) if parsed.get("duration") else None,
        "no_tests_collected": bool(
            (isinstance(total_collected, int) and total_collected == 0)
            or (isinstance(total, int) and total == 0)
        ),
    }


def parse_pytest_junit_xml(content: str) -> PytestSummary:
    """Parse summary counts from a JUnit XML report."""
    testsuite_match = _TESTSUITE_TAG_PATTERN.search(content)
    if testsuite_match is None:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "xfailed": 0,
            "xpassed": 0,
            "duration_seconds": None,
            "no_tests_collected": True,
        }

    attributes = {
        match.group("key"): match.group("value")
        for match in _XML_ATTR_PATTERN.finditer(testsuite_match.group("attrs"))
    }

    tests = int(attributes.get("tests", "0"))
    failures = int(attributes.get("failures", "0"))
    errors = int(attributes.get("errors", "0"))
    skipped = int(attributes.get("skipped", "0"))
    duration = float(attributes["time"]) if "time" in attributes else None

    passed = max(0, tests - failures - errors - skipped)
    return {
        "passed": passed,
        "failed": failures,
        "skipped": skipped,
        "errors": errors,
        "xfailed": 0,
        "xpassed": 0,
        "duration_seconds": duration,
        "no_tests_collected": tests == 0,
    }


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
