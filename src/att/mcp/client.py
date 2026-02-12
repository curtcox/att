"""ATT MCP client management with health/backoff handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

import httpx


class ServerStatus(StrEnum):
    """Availability state for an external MCP server."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


@dataclass(slots=True)
class ExternalServer:
    """Connected external MCP server and health metadata."""

    name: str
    url: str
    status: ServerStatus = ServerStatus.HEALTHY
    last_error: str | None = None
    retry_count: int = 0
    last_checked_at: datetime | None = None
    next_retry_at: datetime | None = None

    @property
    def healthy(self) -> bool:
        """Backwards-compatible health bool view."""
        return self.status is ServerStatus.HEALTHY


@dataclass(slots=True)
class ConnectionEvent:
    """Connection status transition event."""

    server: str
    from_status: ServerStatus
    to_status: ServerStatus
    reason: str
    timestamp: datetime


class HealthProbe(Protocol):
    """Async probe protocol for MCP health checks."""

    async def __call__(self, server: ExternalServer) -> tuple[bool, str | None]:
        """Return (healthy, error_message)."""


class MCPClientManager:
    """Track external MCP server availability and retry policy."""

    def __init__(
        self,
        *,
        probe: HealthProbe | None = None,
        max_backoff_seconds: int = 8,
        unreachable_after: int = 3,
    ) -> None:
        self._servers: dict[str, ExternalServer] = {}
        self._events: list[ConnectionEvent] = []
        self._probe = probe
        self._max_backoff_seconds = max_backoff_seconds
        self._unreachable_after = unreachable_after

    def register(self, name: str, url: str) -> ExternalServer:
        """Register or replace a server definition."""
        server = ExternalServer(name=name, url=url)
        self._servers[name] = server
        return server

    def unregister(self, name: str) -> None:
        """Remove one server."""
        self._servers.pop(name, None)

    def get(self, name: str) -> ExternalServer | None:
        """Fetch one registered server."""
        return self._servers.get(name)

    def list_servers(self) -> list[ExternalServer]:
        """List known servers by name."""
        return sorted(self._servers.values(), key=lambda item: item.name)

    def list_events(self) -> list[ConnectionEvent]:
        """List connection status transition events."""
        return list(self._events)

    def choose_server(self, preferred: list[str] | None = None) -> ExternalServer | None:
        """Choose best available server with healthy-first policy."""
        ordered = self._order_candidates(preferred)
        for candidate in ordered:
            if candidate.status is ServerStatus.HEALTHY:
                return candidate
        for candidate in ordered:
            if candidate.status is ServerStatus.DEGRADED:
                return candidate
        return None

    def should_retry(self, name: str, *, now: datetime | None = None) -> bool:
        """Check whether retry window is open for a server."""
        server = self._servers.get(name)
        if server is None:
            return False
        if server.next_retry_at is None:
            return True
        current = now or datetime.now(UTC)
        return current >= server.next_retry_at

    async def health_check_server(self, name: str) -> ExternalServer | None:
        """Run health check for one server and update status/backoff."""
        server = self._servers.get(name)
        if server is None:
            return None
        if not self.should_retry(name):
            return server
        probe = self._probe or self._default_probe
        healthy, error = await probe(server)
        self.record_check_result(name, healthy=healthy, error=error)
        return self._servers.get(name)

    async def health_check_all(self) -> list[ExternalServer]:
        """Run health checks for all retry-eligible servers."""
        results: list[ExternalServer] = []
        for name in sorted(self._servers):
            checked = await self.health_check_server(name)
            if checked is not None:
                results.append(checked)
        return results

    def record_check_result(
        self,
        name: str,
        *,
        healthy: bool,
        error: str | None = None,
        checked_at: datetime | None = None,
    ) -> None:
        """Apply one health check result and update retry metadata."""
        server = self._servers.get(name)
        if server is None:
            return
        when = checked_at or datetime.now(UTC)
        old_status = server.status
        if healthy:
            server.status = ServerStatus.HEALTHY
            server.last_error = None
            server.retry_count = 0
            server.next_retry_at = None
        else:
            server.retry_count += 1
            if server.retry_count >= self._unreachable_after:
                server.status = ServerStatus.UNREACHABLE
            else:
                server.status = ServerStatus.DEGRADED
            server.last_error = error or "health check failed"
            backoff_seconds = min(
                2 ** (server.retry_count - 1),
                self._max_backoff_seconds,
            )
            server.next_retry_at = when + timedelta(seconds=backoff_seconds)
        server.last_checked_at = when
        if server.status is not old_status:
            self._events.append(
                ConnectionEvent(
                    server=name,
                    from_status=old_status,
                    to_status=server.status,
                    reason=server.last_error or "healthy",
                    timestamp=when,
                )
            )

    def mark_degraded(self, name: str, *, reason: str = "manual degrade") -> None:
        """Manual degrade marker for one server."""
        self.record_check_result(name, healthy=False, error=reason)

    def mark_healthy(self, name: str) -> None:
        """Manual healthy marker for one server."""
        self.record_check_result(name, healthy=True)

    @staticmethod
    async def _default_probe(server: ExternalServer) -> tuple[bool, str | None]:
        """Default HTTP health probe against `/health`."""
        health_url = f"{server.url.rstrip('/')}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
            if response.status_code < 400:
                return True, None
            return False, f"http {response.status_code}"
        except httpx.HTTPError as exc:
            return False, str(exc)

    def _order_candidates(self, preferred: list[str] | None) -> list[ExternalServer]:
        if not preferred:
            return self.list_servers()
        preferred_set = set(preferred)
        prioritized = [self._servers[name] for name in preferred if name in self._servers]
        others = [server for server in self.list_servers() if server.name not in preferred_set]
        return [*prioritized, *others]
