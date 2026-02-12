"""Debug routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_debug_log_store, get_debug_manager, get_project_manager
from att.api.routes.common import require_project
from att.core.debug_manager import DebugManager
from att.core.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/debug", tags=["debug"])


@router.get("/errors")
async def debug_errors(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    debug: DebugManager = Depends(get_debug_manager),
    log_store: dict[str, list[str]] = Depends(get_debug_log_store),
) -> dict[str, list[str]]:
    await require_project(project_id, manager)
    logs = log_store.get(project_id, [])
    return {"errors": debug.errors(logs)}


@router.get("/logs")
async def debug_logs(
    project_id: str,
    query: str = "",
    manager: ProjectManager = Depends(get_project_manager),
    debug: DebugManager = Depends(get_debug_manager),
    log_store: dict[str, list[str]] = Depends(get_debug_log_store),
) -> dict[str, list[str]]:
    await require_project(project_id, manager)
    logs = log_store.get(project_id, [])
    filtered = debug.filter_logs(logs, query) if query else logs
    return {"logs": filtered}
