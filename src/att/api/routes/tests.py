"""Test routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from att.api.deps import get_project_manager, get_test_result_store, get_test_runner
from att.api.routes.common import require_project
from att.api.schemas.test import RunTestRequest
from att.core.project_manager import ProjectManager
from att.core.test_runner import TestResultPayload, TestRunner

router = APIRouter(prefix="/api/v1/projects/{project_id}/test", tags=["test"])


@router.post("/run")
async def run_tests(
    project_id: str,
    request: RunTestRequest,
    manager: ProjectManager = Depends(get_project_manager),
    test_runner: TestRunner = Depends(get_test_runner),
    test_store: dict[str, TestResultPayload] = Depends(get_test_result_store),
) -> TestResultPayload:
    project = await require_project(project_id, manager)
    result = test_runner.run(
        project.path,
        suite=request.suite,
        markers=request.markers,
        timeout_seconds=request.timeout_seconds,
    )
    payload = result.as_payload()
    test_store[project_id] = payload
    return payload


@router.get("/results")
async def test_results(
    project_id: str,
    manager: ProjectManager = Depends(get_project_manager),
    test_store: dict[str, TestResultPayload] = Depends(get_test_result_store),
) -> TestResultPayload:
    await require_project(project_id, manager)
    return test_store.get(project_id, {"status": "no_results"})
