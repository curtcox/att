"""Git routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_git_manager, get_project_manager
from att.api.routes.common import require_project
from att.api.schemas.git import BranchRequest, CommitRequest, PushRequest
from att.core.git_manager import GitManager
from att.core.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/git", tags=["git"])


@router.get("/status")
async def git_status(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    return {"status": git.status(project.path).output}


@router.post("/commit")
async def git_commit(
    project_id: str,
    request: CommitRequest,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    result = git.commit(project.path, request.message)
    return {"result": result.output}


@router.post("/push")
async def git_push(
    project_id: str,
    request: PushRequest,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    result = git.push(project.path, request.remote, request.branch)
    return {"result": result.output}


@router.post("/branch")
async def git_branch(
    project_id: str,
    request: BranchRequest,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    result = git.branch(project.path, request.name, checkout=request.checkout)
    return {"result": result.output}


@router.get("/log")
async def git_log(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    result = git.log(project.path)
    return {"log": result.output}


@router.get("/actions")
async def git_actions(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    await require_project(project_id, manager)
    return {"status": "not_implemented"}


@router.post("/pr")
async def git_pr_create(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    await require_project(project_id, manager)
    return {"status": "not_implemented"}


@router.post("/pr/merge")
async def git_pr_merge(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    await require_project(project_id, manager)
    return {"status": "not_implemented"}


@router.get("/pr/reviews")
async def git_pr_reviews(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    await require_project(project_id, manager)
    return {"status": "not_implemented"}
