"""Git routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from att.api.deps import get_git_manager, get_project_manager
from att.api.routes.common import require_project
from att.api.schemas.git import (
    BranchRequest,
    CommitRequest,
    PRCreateRequest,
    PRMergeRequest,
    PushRequest,
)
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
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    try:
        result = git.actions(project.path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {"actions": result.output}


@router.post("/pr")
async def git_pr_create(
    project_id: str,
    request: PRCreateRequest,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    try:
        result = git.pr_create(
            project.path,
            title=request.title,
            body=request.body,
            base=request.base,
            head=request.head,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {"result": result.output}


@router.post("/pr/merge")
async def git_pr_merge(
    project_id: str,
    request: PRMergeRequest,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    try:
        result = git.pr_merge(
            project.path,
            pull_request=request.pull_request,
            strategy=request.strategy,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {"result": result.output}


@router.get("/pr/reviews")
async def git_pr_reviews(
    project_id: str,
    pull_request: str,
    manager: ProjectManager = Depends(get_project_manager),
    git: GitManager = Depends(get_git_manager),
) -> dict[str, str]:
    project = await require_project(project_id, manager)
    try:
        result = git.pr_reviews(project.path, pull_request=pull_request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return {"reviews": result.output}
