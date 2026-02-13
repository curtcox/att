"""Runtime routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_project_manager, get_runtime_manager
from att.api.routes.common import require_project
from att.api.schemas.runtime import RuntimeStartRequest
from att.core.project_manager import ProjectManager
from att.core.runtime_manager import RuntimeManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/runtime", tags=["runtime"])


@router.post("/start")
async def runtime_start(
    project_id: str,
    request: RuntimeStartRequest,
    manager: ProjectManager = Depends(get_project_manager),
    runtime: RuntimeManager = Depends(get_runtime_manager),
) -> dict[str, bool | int | None]:
    project = await require_project(project_id, manager)
    state = runtime.start(project.path, request.config_path)
    return {"running": state.running, "pid": state.pid}


@router.post("/stop")
async def runtime_stop(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    runtime: RuntimeManager = Depends(get_runtime_manager),
) -> dict[str, bool | int | None]:
    await require_project(project_id, manager)
    state = runtime.stop()
    return {"running": state.running, "pid": state.pid}


@router.get("/status")
async def runtime_status(
    project_id: str,
    health_target: str | None = None,
    manager: ProjectManager = Depends(get_project_manager),
    runtime: RuntimeManager = Depends(get_runtime_manager),
) -> dict[str, bool | int | str | None]:
    await require_project(project_id, manager)
    probe = runtime.probe_health(url=health_target)
    return {
        "running": probe.running,
        "pid": probe.pid,
        "returncode": probe.returncode,
        "healthy": probe.healthy,
        "health_probe": probe.probe,
        "health_reason": probe.reason,
        "health_checked_at": probe.checked_at.isoformat(),
        "health_http_status": probe.http_status,
        "health_command": probe.command,
    }


@router.get("/logs")
async def runtime_logs(
    project_id: str,
    cursor: int | None = None,
    limit: int | None = None,
    manager: ProjectManager = Depends(get_project_manager),
    runtime: RuntimeManager = Depends(get_runtime_manager),
) -> dict[str, list[str] | int | bool]:
    await require_project(project_id, manager)
    log_read = runtime.read_logs(cursor=cursor, limit=limit)
    return {
        "logs": log_read.logs,
        "cursor": log_read.cursor,
        "start_cursor": log_read.start_cursor,
        "end_cursor": log_read.end_cursor,
        "truncated": log_read.truncated,
        "has_more": log_read.has_more,
    }
