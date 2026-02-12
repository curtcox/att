"""Workflow orchestration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_project_manager, get_tool_orchestrator
from att.api.routes.common import require_project
from att.api.schemas.workflows import RunChangeWorkflowRequest, RunChangeWorkflowResponse
from att.core.project_manager import ProjectManager
from att.core.tool_orchestrator import ToolOrchestrator

router = APIRouter(prefix="/api/v1/projects/{project_id}/workflows", tags=["workflows"])


@router.post("/change-test", response_model=RunChangeWorkflowResponse)
async def run_change_workflow(
    project_id: str,
    request: RunChangeWorkflowRequest,
    manager: ProjectManager = Depends(get_project_manager),
    orchestrator: ToolOrchestrator = Depends(get_tool_orchestrator),
) -> RunChangeWorkflowResponse:
    project = await require_project(project_id, manager)
    workflow_result = await orchestrator.run_change_workflow(
        project_id=project_id,
        project_path=project.path,
        rel_path=request.file_path,
        new_content=request.content,
        suite=request.suite,
        commit_message=request.commit_message,
    )
    return RunChangeWorkflowResponse(
        diff=workflow_result.diff,
        test_command=workflow_result.test_result.command,
        test_returncode=workflow_result.test_result.returncode,
        test_output=workflow_result.test_result.output,
        committed=workflow_result.committed,
        commit_output=workflow_result.commit_output,
        event_ids=[event.id for event in workflow_result.events],
    )
