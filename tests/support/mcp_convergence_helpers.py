from __future__ import annotations

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
