"""Deploy routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_deploy_manager, get_project_manager
from att.api.routes.common import require_project
from att.api.schemas.deploy import DeployRunRequest
from att.core.deploy_manager import DeployManager
from att.core.project_manager import ProjectManager

router = APIRouter(prefix="/api/v1/projects/{project_id}/deploy", tags=["deploy"])


@router.post("/build")
async def deploy_build(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    deploy: DeployManager = Depends(get_deploy_manager),
) -> dict[str, str | bool]:
    project = await require_project(project_id, manager)
    status = deploy.build(project.path)
    return {"built": status.built, "running": status.running, "message": status.message}


@router.post("/run")
async def deploy_run(
    project_id: str,
    request: DeployRunRequest,
    manager: ProjectManager = Depends(get_project_manager),
    deploy: DeployManager = Depends(get_deploy_manager),
) -> dict[str, str | bool]:
    project = await require_project(project_id, manager)
    status = deploy.run(project.path, request.config_path)
    return {"built": status.built, "running": status.running, "message": status.message}


@router.get("/status")
async def deploy_status(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    deploy: DeployManager = Depends(get_deploy_manager),
) -> dict[str, str | bool]:
    await require_project(project_id, manager)
    status = deploy.status()
    return {"built": status.built, "running": status.running, "message": status.message}
