"""Self-bootstrap routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_project_manager, get_self_bootstrap_manager
from att.api.routes.common import require_project
from att.api.schemas.self_bootstrap import SelfBootstrapRequestModel, SelfBootstrapResponseModel
from att.core.project_manager import ProjectManager
from att.core.self_bootstrap_manager import SelfBootstrapManager, SelfBootstrapRequest

router = APIRouter(prefix="/api/v1/projects/{project_id}/self-bootstrap", tags=["self-bootstrap"])


@router.post("/run", response_model=SelfBootstrapResponseModel)
async def run_self_bootstrap(
    project_id: str,
    request: SelfBootstrapRequestModel,
    manager: ProjectManager = Depends(get_project_manager),
    bootstrap: SelfBootstrapManager = Depends(get_self_bootstrap_manager),
) -> SelfBootstrapResponseModel:
    project = await require_project(project_id, manager)
    result = await bootstrap.execute(
        SelfBootstrapRequest(
            project_id=project_id,
            project_path=project.path,
            file_path=request.file_path,
            content=request.content,
            commit_message=request.commit_message,
            suite=request.suite,
            branch_name=request.branch_name,
            ci_timeout_seconds=request.ci_timeout_seconds,
            ci_initial_poll_seconds=request.ci_initial_poll_seconds,
            ci_max_poll_seconds=request.ci_max_poll_seconds,
            health_check_target=request.health_check_target,
        )
    )
    return SelfBootstrapResponseModel(
        branch_name=result.branch_name,
        committed=result.committed,
        pushed=result.pushed,
        ci_status=result.ci_status,
        health_status=result.health_status,
        success=result.success,
        test_returncode=result.workflow_result.test_result.returncode,
        event_ids=[event.id for event in result.workflow_result.events],
    )
