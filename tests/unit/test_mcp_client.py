from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from att.mcp.client import MCPClientManager, ServerStatus


@pytest.mark.asyncio
async def test_health_check_probe_updates_status_and_logs_transition() -> None:
    async def flaky_probe(_: object) -> tuple[bool, str | None]:
        return False, "timeout"

    manager = MCPClientManager(probe=flaky_probe, unreachable_after=2)
    manager.register("codex", "http://codex.local")

    await manager.health_check_server("codex")
    server = manager.get("codex")
    assert server is not None
    assert server.status is ServerStatus.DEGRADED
    assert server.retry_count == 1
    assert server.last_error == "timeout"
    server.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)

    await manager.health_check_server("codex")
    server = manager.get("codex")
    assert server is not None
    assert server.status is ServerStatus.UNREACHABLE
    assert server.retry_count == 2

    events = manager.list_events()
    assert len(events) == 2
    assert events[0].to_status is ServerStatus.DEGRADED
    assert events[1].to_status is ServerStatus.UNREACHABLE


@pytest.mark.asyncio
async def test_health_check_recovery_resets_backoff() -> None:
    states = [(False, "temporary"), (True, None)]

    async def toggled_probe(_: object) -> tuple[bool, str | None]:
        return states.pop(0)

    manager = MCPClientManager(probe=toggled_probe)
    manager.register("github", "http://github.local")

    await manager.health_check_server("github")
    degraded = manager.get("github")
    assert degraded is not None
    assert degraded.status is ServerStatus.DEGRADED
    assert degraded.next_retry_at is not None

    manager.record_check_result("github", healthy=True)
    recovered = manager.get("github")
    assert recovered is not None
    assert recovered.status is ServerStatus.HEALTHY
    assert recovered.retry_count == 0
    assert recovered.next_retry_at is None


@pytest.mark.asyncio
async def test_should_retry_observes_next_retry_window() -> None:
    manager = MCPClientManager()
    manager.register("terminal", "http://terminal.local")

    now = datetime.now(UTC)
    manager.record_check_result(
        "terminal",
        healthy=False,
        error="down",
        checked_at=now,
    )

    assert manager.should_retry("terminal", now=now) is False
    assert manager.should_retry("terminal", now=now + timedelta(seconds=1)) is True


def test_choose_server_prefers_healthy_then_degraded() -> None:
    manager = MCPClientManager()
    manager.register("a", "http://a.local")
    manager.register("b", "http://b.local")

    manager.record_check_result("a", healthy=False, error="slow")

    selected = manager.choose_server()
    assert selected is not None
    assert selected.name == "b"

    manager.record_check_result("b", healthy=False, error="down")
    fallback = manager.choose_server(preferred=["a", "b"])
    assert fallback is not None
    assert fallback.name == "a"
