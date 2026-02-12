"""Project routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from att.api.deps import get_project_manager
from att.api.schemas.projects import CloneProjectRequest, CreateProjectRequest, ProjectsResponse
from att.core.project_manager import CreateProjectInput, ProjectManager
from att.models.project import Project

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=ProjectsResponse)
async def list_projects(manager: ProjectManager = Depends(get_project_manager)) -> ProjectsResponse:
    return ProjectsResponse(items=await manager.list())


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    project = await manager.create(
        CreateProjectInput(
            name=request.name,
            path=request.path,
            git_remote=request.git_remote,
            nat_config_path=request.nat_config_path,
        )
    )
    return {"id": project.id}


@router.post("/clone", status_code=status.HTTP_201_CREATED)
async def clone_project(
    request: CloneProjectRequest,
    manager: ProjectManager = Depends(get_project_manager),
) -> dict[str, str]:
    try:
        project = await manager.clone(
            CreateProjectInput(
                name=request.name,
                path=request.path,
                git_remote=request.git_remote,
                nat_config_path=request.nat_config_path,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"id": project.id}


@router.get("/{project_id}")
async def get_project(
    project_id: str, manager: ProjectManager = Depends(get_project_manager)
) -> dict[str, Project]:
    project = await manager.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"project": project}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> None:
    await manager.delete(project_id)


@router.get("/{project_id}/download")
async def download_project_archive(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
) -> FileResponse:
    try:
        archive_path = await manager.download(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=archive_path.name,
    )
