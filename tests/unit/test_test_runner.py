from __future__ import annotations

import subprocess
from pathlib import Path

from att.core.test_runner import (
    TestRunner,
    parse_pytest_json_report,
    parse_pytest_junit_xml,
    parse_pytest_output_summary,
)


def test_run_unit_tests_returns_results(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int | None,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="================ 2 passed, 1 skipped in 0.54s ================\n",
            stderr="",
        )

    monkeypatch.setattr("att.core.test_runner.subprocess.run", fake_run)

    runner = TestRunner()
    result = runner.run(tmp_path, suite="unit")

    assert captured["command"] == ["pytest", "tests/unit"]
    assert captured["cwd"] == tmp_path
    assert captured["check"] is False
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["timeout"] is None
    assert result.returncode == 0
    assert result.passed == 2
    assert result.skipped == 1
    assert result.duration_seconds == 0.54
    assert result.no_tests_collected is False
    assert result.timed_out is False


def test_run_supports_specific_target_markers_and_timeout(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int | None,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["timeout"] = timeout
        del cwd, check, capture_output, text
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("att.core.test_runner.subprocess.run", fake_run)

    runner = TestRunner()
    _ = runner.run(
        tmp_path,
        suite="tests/unit/test_sample.py::test_happy_path",
        markers="slow and gpu",
        timeout_seconds=45,
    )

    assert captured["command"] == [
        "pytest",
        "tests/unit/test_sample.py::test_happy_path",
        "-m",
        "slow and gpu",
    ]
    assert captured["timeout"] == 45


def test_run_timeout_returns_timed_out_result(monkeypatch, tmp_path: Path) -> None:
    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int | None,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, check, capture_output, text, timeout
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=5,
            output="partial output\n",
            stderr="timeout stderr\n",
        )

    monkeypatch.setattr("att.core.test_runner.subprocess.run", fake_run)

    runner = TestRunner()
    result = runner.run(tmp_path, suite="integration", timeout_seconds=5)

    assert result.returncode == 124
    assert result.timed_out is True
    assert "partial output" in result.output
    assert "timeout stderr" in result.output


def test_parse_pytest_output_summary() -> None:
    summary = parse_pytest_output_summary(
        """
==================== short test summary info ====================
FAILED tests/test_a.py::test_nope - assert 1 == 2
================ 1 failed, 3 passed, 2 skipped, 1 error in 2.15s ================
        """.strip()
    )
    assert summary["failed"] == 1
    assert summary["passed"] == 3
    assert summary["skipped"] == 2
    assert summary["errors"] == 1
    assert summary["duration_seconds"] == 2.15
    assert summary["no_tests_collected"] is False


def test_parse_pytest_output_summary_no_tests() -> None:
    summary = parse_pytest_output_summary("no tests ran in 0.03s")
    assert summary["passed"] == 0
    assert summary["failed"] == 0
    assert summary["no_tests_collected"] is True
    assert summary["duration_seconds"] == 0.03


def test_parse_pytest_json_report() -> None:
    summary = parse_pytest_json_report(
        """
{
  "summary": {
    "collected": 5,
    "total": 5,
    "passed": 3,
    "failed": 1,
    "skipped": 1,
    "errors": 0
  },
  "duration": 1.75
}
        """.strip()
    )
    assert summary["passed"] == 3
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["errors"] == 0
    assert summary["duration_seconds"] == 1.75
    assert summary["no_tests_collected"] is False


def test_parse_pytest_junit_xml() -> None:
    summary = parse_pytest_junit_xml(
        '<testsuite tests="4" failures="1" errors="1" skipped="1" time="0.77"></testsuite>'
    )
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["errors"] == 1
    assert summary["skipped"] == 1
    assert summary["duration_seconds"] == 0.77
    assert summary["no_tests_collected"] is False
