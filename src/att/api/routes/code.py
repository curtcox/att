"""Code routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_code_manager, get_project_manager
from att.api.routes.common import require_project
from att.api.schemas.code import SearchRequest, WriteFileRequest
from att.core.code_manager import CodeManager
from att.core.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/files", tags=["code"])


@router.get("")
async def list_files(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    code: CodeManager = Depends(get_code_manager),
) -> dict[str, list[str]]:
    project = await require_project(project_id, manager)
    files = [str(path.relative_to(project.path)) for path in code.list_files(project.path)]
    return {"files": files}


@router.post("/search")
async def search_files(
    project_id: str,
    request: SearchRequest,
    manager: ProjectManager = Depends(get_project_manager),
    code: CodeManager = Depends(get_code_manager),
) -> dict[str, list[str]]:
    project = await require_project(project_id, manager)
    matches = [
        str(path.relative_to(project.path)) for path in code.search(project.path, request.pattern)
    ]
    return {"matches": matches}


@router.get("/diff")
async def file_diff(
    project_id: str,
    original: str,
    updated: str,
    from_name: str,
    to_name: str,
    manager: ProjectManager = Depends(get_project_manager),
    code: CodeManager = Depends(get_code_manager),
) -> dict[str, str]:
    await require_project(project_id, manager)
    return {"diff": code.diff(original, updated, from_name=from_name, to_name=to_name)}


@router.get("/{file_path:path}")
async def read_file(
    project_id: str,
    file_path: str,
    manager: ProjectManager = Depends(get_project_manager),
    code: CodeManager = Depends(get_code_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    return {"content": code.read_file(project.path, file_path)}


@router.put("/{file_path:path}")
async def write_file(
    project_id: str,
    file_path: str,
    request: WriteFileRequest,
    manager: ProjectManager = Depends(get_project_manager),
    code: CodeManager = Depends(get_code_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    code.write_file(project.path, file_path, request.content)
    return {"status": "updated"}
