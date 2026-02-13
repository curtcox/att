from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi.testclient import TestClient


def expected_phases_for_server(
    phases: list[str],
    servers: list[str],
    *,
    server: str,
) -> list[str]:
    return [
        phase for phase, event_server in zip(phases, servers, strict=True) if event_server == server
    ]


def assert_invocation_event_filters(
    client: TestClient,
    *,
    request_id: str,
    server: str,
    expected_phases: list[str],
    method: str | None = None,
) -> None:
    params: dict[str, str | int] = {
        "server": server,
        "request_id": request_id,
    }
    if method is not None:
        params["method"] = method

    filtered = client.get("/api/v1/mcp/invocation-events", params=params)
    assert filtered.status_code == 200
    assert [item["phase"] for item in filtered.json()["items"]] == expected_phases

    limited = client.get(
        "/api/v1/mcp/invocation-events",
        params={**params, "limit": 1},
    )
    assert limited.status_code == 200
    assert [item["phase"] for item in limited.json()["items"]] == expected_phases[-1:]


def assert_connection_event_filters(
    client: TestClient,
    *,
    request_id: str,
    server: str,
    expected_statuses: list[str],
) -> None:
    params: dict[str, str | int] = {
        "server": server,
        "correlation_id": request_id,
    }
    filtered = client.get("/api/v1/mcp/events", params=params)
    assert filtered.status_code == 200
    assert [item["to_status"] for item in filtered.json()["items"]] == expected_statuses

    limited = client.get("/api/v1/mcp/events", params={**params, "limit": 1})
    assert limited.status_code == 200
    assert [item["to_status"] for item in limited.json()["items"]] == expected_statuses[-1:]


def extract_request_id_from_invocation_event_delta(
    client: TestClient,
    *,
    previous_count: int,
    expected_phases: list[str] | None = None,
) -> str:
    response = client.get("/api/v1/mcp/invocation-events")
    assert response.status_code == 200
    events: list[dict[str, Any]] = response.json()["items"][previous_count:]
    if expected_phases is not None:
        assert [str(item["phase"]) for item in events] == expected_phases
    request_ids = {str(item["request_id"]) for item in events}
    assert len(request_ids) == 1
    return request_ids.pop()


def collect_invocation_events_for_requests(
    client: TestClient,
    *,
    request_ids: Iterable[str],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for request_id in request_ids:
        response = client.get(
            "/api/v1/mcp/invocation-events",
            params={"request_id": request_id},
        )
        assert response.status_code == 200
        events.extend(response.json()["items"])
    return events


def expected_call_order_from_phase_starts(
    events: Iterable[dict[str, Any]],
) -> list[tuple[str, str]]:
    phase_to_method = {
        "initialize_start": "initialize",
        "invoke_start": None,
    }
    return [
        (str(item["server"]), phase_to_method[str(item["phase"])] or str(item["method"]))
        for item in events
        if str(item["phase"]) in {"initialize_start", "invoke_start"}
    ]


def assert_call_order_subsequence(
    *,
    observed_call_order: list[tuple[str, str]],
    expected_call_order: list[tuple[str, str]],
) -> None:
    cursor = 0
    for call in observed_call_order:
        while cursor < len(expected_call_order) and expected_call_order[cursor] != call:
            cursor += 1
        assert cursor < len(expected_call_order), (
            f"missing call-order tuple in phase stream: {call}"
        )
        cursor += 1
