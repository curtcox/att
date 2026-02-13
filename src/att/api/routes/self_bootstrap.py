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
            create_pr=request.create_pr,
            auto_merge_on_ci_success=request.auto_merge_on_ci_success,
            deploy_target=request.deploy_target,
            requested_release_id=request.requested_release_id,
            previous_release_id=request.previous_release_id,
            rollback_release_id=request.rollback_release_id,
            rollback_on_deploy_failure=request.rollback_on_deploy_failure,
            rollback_on_restart_watchdog_failure=request.rollback_on_restart_watchdog_failure,
            rollback_on_health_failure=request.rollback_on_health_failure,
            deployment_context=request.deployment_context,
            health_check_target=request.health_check_target,
            health_check_retries=request.health_check_retries,
            health_check_interval_seconds=request.health_check_interval_seconds,
            restart_watchdog_retries=request.restart_watchdog_retries,
            restart_watchdog_interval_seconds=request.restart_watchdog_interval_seconds,
        )
    )
    return SelfBootstrapResponseModel(
        branch_name=result.branch_name,
        committed=result.committed,
        pushed=result.pushed,
        ci_status=result.ci_status,
        pr_url=result.pr_url,
        merged=result.merged,
        restart_watchdog_status=result.restart_watchdog_status,
        restart_watchdog_reason=result.restart_watchdog_reason,
        health_status=result.health_status,
        rollback_performed=result.rollback_performed,
        rollback_succeeded=result.rollback_succeeded,
        deployed_release_id=result.deployed_release_id,
        rollback_target_release_id=result.rollback_target_release_id,
        release_metadata_source=result.release_metadata_source,
        rollback_policy_status=result.rollback_policy_status,
        rollback_policy_reason=result.rollback_policy_reason,
        rollback_target_valid=result.rollback_target_valid,
        rollback_failure_class=result.rollback_failure_class,
        rollback_deployment_context=result.rollback_deployment_context,
        success=result.success,
        test_returncode=result.workflow_result.test_result.returncode,
        event_ids=[event.id for event in result.workflow_result.events],
    )
