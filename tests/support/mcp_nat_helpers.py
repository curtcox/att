from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import httpx


class ModelPayload:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, *, mode: str = "python", exclude_none: bool = False) -> dict[str, Any]:
        del mode, exclude_none
        return self._payload


class APIFakeNatSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def initialize(self) -> ModelPayload:
        return ModelPayload(
            {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "nat"},
                "capabilities": {"tools": {}, "resources": {}},
            }
        )

    async def send_notification(
        self,
        notification: object,
        related_request_id: str | int | None = None,
    ) -> None:
        del notification, related_request_id

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: object | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> ModelPayload:
        del read_timeout_seconds, progress_callback, meta
        return ModelPayload(
            {
                "content": [{"type": "text", "text": "ok"}],
                "structuredContent": {
                    "session_id": self.session_id,
                    "tool": name,
                    "arguments": arguments or {},
                },
                "isError": False,
            }
        )

    async def read_resource(self, uri: object) -> ModelPayload:
        return ModelPayload(
            {
                "contents": [{"uri": str(uri), "mimeType": "text/plain", "text": "data"}],
            }
        )


class APIFakeNatSessionFactory:
    def __init__(self) -> None:
        self.created = 0
        self.closed = 0

    @asynccontextmanager
    async def __call__(self, _: str) -> Any:
        self.created += 1
        try:
            yield APIFakeNatSession(session_id=f"session-{self.created}")
        finally:
            self.closed += 1


class FakeNatSession:
    def __init__(self, *, session_id: str = "session-0") -> None:
        self.session_id = session_id
        self.initialized = False
        self.calls: list[tuple[str, str]] = []
        self.fail_with: Exception | None = None

    async def initialize(self) -> ModelPayload:
        self.calls.append(("session", "initialize"))
        self.initialized = True
        return ModelPayload(
            {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "nat"},
                "capabilities": {"tools": {}, "resources": {}},
            }
        )

    async def send_notification(
        self,
        notification: object,
        related_request_id: str | int | None = None,
    ) -> None:
        del notification, related_request_id
        self.calls.append(("session", "notifications/initialized"))

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: object | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> ModelPayload:
        del read_timeout_seconds, progress_callback, meta
        self.calls.append(("tool", name))
        if self.fail_with is not None:
            raise self.fail_with
        return ModelPayload(
            {
                "content": [{"type": "text", "text": "ok"}],
                "structuredContent": {
                    "arguments": arguments or {},
                    "session_id": self.session_id,
                },
                "isError": False,
            }
        )

    async def read_resource(self, uri: object) -> ModelPayload:
        self.calls.append(("resource", str(uri)))
        return ModelPayload(
            {
                "contents": [{"uri": str(uri), "mimeType": "text/plain", "text": "data"}],
            }
        )


class FakeNatSessionFactory:
    def __init__(self) -> None:
        self.created = 0
        self.closed = 0
        self.sessions: list[FakeNatSession] = []

    @asynccontextmanager
    async def __call__(self, _: str) -> Any:
        session = FakeNatSession(session_id=f"session-{self.created + 1}")
        self.created += 1
        self.sessions.append(session)
        try:
            yield session
        finally:
            self.closed += 1


class ClusterNatSession:
    def __init__(
        self,
        *,
        server_name: str,
        session_id: str,
        factory: ClusterNatSessionFactory,
    ) -> None:
        self.server_name = server_name
        self.session_id = session_id
        self.factory = factory

    async def initialize(self) -> ModelPayload:
        scripted = self.factory.consume_failure_action(self.server_name, "initialize")
        if scripted == "timeout":
            msg = f"{self.server_name} initialize timed out"
            raise httpx.ReadTimeout(msg)
        if scripted == "error":
            msg = f"{self.server_name} initialize unavailable"
            raise RuntimeError(msg)
        if scripted is None and self.server_name in self.factory.fail_on_timeout_initialize:
            msg = f"{self.server_name} initialize timed out"
            raise httpx.ReadTimeout(msg)
        self.factory.calls.append((self.server_name, self.session_id, "initialize"))
        return ModelPayload(
            {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": self.server_name},
                "capabilities": {"tools": {}, "resources": {}},
            }
        )

    async def send_notification(
        self,
        notification: object,
        related_request_id: str | int | None = None,
    ) -> None:
        del notification, related_request_id
        self.factory.calls.append((self.server_name, self.session_id, "notifications/initialized"))

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: object | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> ModelPayload:
        del read_timeout_seconds, progress_callback, meta
        self.factory.calls.append((self.server_name, self.session_id, "tools/call"))
        scripted = self.factory.consume_failure_action(self.server_name, "tools/call")
        if scripted == "timeout":
            msg = f"{self.server_name} timed out"
            raise httpx.ReadTimeout(msg)
        if scripted == "error":
            msg = f"{self.server_name} unavailable"
            raise RuntimeError(msg)
        if scripted is None:
            if self.server_name in self.factory.fail_on_timeout_tool_calls:
                msg = f"{self.server_name} timed out"
                raise httpx.ReadTimeout(msg)
            if self.server_name in self.factory.fail_on_tool_calls:
                msg = f"{self.server_name} unavailable"
                raise RuntimeError(msg)
        return ModelPayload(
            {
                "content": [{"type": "text", "text": "ok"}],
                "structuredContent": {
                    "session_id": self.session_id,
                    "server": self.server_name,
                    "tool": name,
                    "arguments": arguments or {},
                },
                "isError": False,
            }
        )

    async def read_resource(self, uri: object) -> ModelPayload:
        self.factory.calls.append((self.server_name, self.session_id, "resources/read"))
        scripted = self.factory.consume_failure_action(self.server_name, "resources/read")
        if scripted == "timeout":
            msg = f"{self.server_name} timed out"
            raise httpx.ReadTimeout(msg)
        if scripted == "error":
            msg = f"{self.server_name} unavailable"
            raise RuntimeError(msg)
        if scripted is None:
            if self.server_name in self.factory.fail_on_timeout_resource_reads:
                msg = f"{self.server_name} timed out"
                raise httpx.ReadTimeout(msg)
            if self.server_name in self.factory.fail_on_resource_reads:
                msg = f"{self.server_name} unavailable"
                raise RuntimeError(msg)
        return ModelPayload(
            {
                "contents": [{"uri": str(uri), "mimeType": "text/plain", "text": "data"}],
            }
        )


class ClusterNatSessionFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.fail_on_timeout_initialize: set[str] = set()
        self.fail_on_tool_calls: set[str] = set()
        self.fail_on_timeout_tool_calls: set[str] = set()
        self.fail_on_resource_reads: set[str] = set()
        self.fail_on_timeout_resource_reads: set[str] = set()
        self.failure_scripts: dict[tuple[str, str], list[str]] = {}
        self.created_by_server: dict[str, int] = {}
        self.closed_by_server: dict[str, int] = {}

    def set_failure_script(self, server_name: str, method: str, script: list[str]) -> None:
        """Set ordered per-server/per-method failure script (e.g., timeout->ok)."""
        self.failure_scripts[(server_name, method)] = list(script)

    def consume_failure_action(self, server_name: str, method: str) -> str | None:
        script = self.failure_scripts.get((server_name, method))
        if not script:
            return None
        action = script.pop(0)
        if action not in {"ok", "timeout", "error"}:
            msg = f"unsupported scripted action: {action}"
            raise ValueError(msg)
        return action

    @asynccontextmanager
    async def __call__(self, endpoint: str) -> Any:
        host = endpoint.split("//", maxsplit=1)[1].split("/", maxsplit=1)[0]
        server_name = host.split(".", maxsplit=1)[0]
        next_index = self.created_by_server.get(server_name, 0) + 1
        self.created_by_server[server_name] = next_index
        session_id = f"{server_name}-session-{next_index}"
        try:
            yield ClusterNatSession(
                server_name=server_name,
                session_id=session_id,
                factory=self,
            )
        finally:
            self.closed_by_server[server_name] = self.closed_by_server.get(server_name, 0) + 1
