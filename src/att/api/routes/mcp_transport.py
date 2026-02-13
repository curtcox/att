"""MCP JSON-RPC transport endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from att.api.deps import (
    get_code_manager,
    get_debug_log_store,
    get_debug_manager,
    get_deploy_manager,
    get_git_manager,
    get_project_manager,
    get_runtime_manager,
    get_test_result_store,
    get_test_runner,
)
from att.core.code_manager import CodeManager
from att.core.debug_manager import DebugManager
from att.core.deploy_manager import DeployManager
from att.core.git_manager import GitManager
from att.core.project_manager import CreateProjectInput, ProjectManager
from att.core.runtime_manager import RuntimeManager
from att.core.test_runner import TestResultPayload, TestRunner
from att.mcp.server import find_tool, registered_resources, registered_tools
from att.mcp.tools.code_tools import CodeToolCall, parse_code_tool_call
from att.mcp.tools.debug_tools import DebugToolCall, parse_debug_tool_call
from att.mcp.tools.deploy_tools import DeployToolCall, parse_deploy_tool_call
from att.mcp.tools.git_tools import GitToolCall, parse_git_tool_call
from att.mcp.tools.project_tools import ProjectToolCall, parse_project_tool_call
from att.mcp.tools.resource_refs import parse_resource_ref
from att.mcp.tools.runtime_tools import RuntimeToolCall, parse_runtime_tool_call
from att.mcp.tools.test_tools import MCPTestToolCall, parse_test_tool_call

router = APIRouter(tags=["mcp-transport"])


def _response(request_id: str | int | None, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


@router.post("/mcp")
async def mcp_transport(
    payload: dict[str, Any],
    project_manager: ProjectManager = Depends(get_project_manager),
    code_manager: CodeManager = Depends(get_code_manager),
    git_manager: GitManager = Depends(get_git_manager),
    runtime_manager: RuntimeManager = Depends(get_runtime_manager),
    test_runner: TestRunner = Depends(get_test_runner),
    debug_manager: DebugManager = Depends(get_debug_manager),
    deploy_manager: DeployManager = Depends(get_deploy_manager),
    test_results: dict[str, TestResultPayload] = Depends(get_test_result_store),
    debug_logs: dict[str, list[str]] = Depends(get_debug_log_store),
) -> dict[str, Any]:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if not isinstance(method, str):
        return _error(request_id, -32600, "Invalid method")
    if not isinstance(params, dict):
        return _error(request_id, -32602, "Invalid params")

    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": "2025-11-25",
                "serverInfo": {"name": "att-mcp", "version": "0.1.0"},
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
            },
        )

    if method == "notifications/initialized":
        return _response(request_id, {})

    if method == "ping":
        return _response(request_id, {})

    if method == "tools/list":
        tools = [
            {"name": tool.name, "description": tool.description} for tool in registered_tools()
        ]
        return _response(request_id, {"tools": tools})

    if method == "resources/list":
        resources = [
            {"uri": resource.uri, "description": resource.description}
            for resource in registered_resources()
        ]
        return _response(request_id, {"resources": resources})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(tool_name, str):
            return _error(request_id, -32602, "Missing tool name")
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "Invalid tool arguments")
        if find_tool(tool_name) is None:
            return _error(request_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = await _handle_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                project_manager=project_manager,
                code_manager=code_manager,
                git_manager=git_manager,
                runtime_manager=runtime_manager,
                test_runner=test_runner,
                debug_manager=debug_manager,
                deploy_manager=deploy_manager,
                test_results=test_results,
                debug_logs=debug_logs,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            return _error(request_id, -32000, str(exc))
        if isinstance(result, dict) and "error" in result:
            return _error(request_id, -32000, str(result["error"]))
        return _response(request_id, result)

    if method == "resources/read":
        uri = params.get("uri")
        if not isinstance(uri, str):
            return _error(request_id, -32602, "Missing resource uri")
        try:
            result = await _handle_resource_read(
                uri=uri,
                project_manager=project_manager,
                code_manager=code_manager,
                git_manager=git_manager,
                runtime_manager=runtime_manager,
                test_results=test_results,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            return _error(request_id, -32000, str(exc))
        if isinstance(result, dict) and result.get("error"):
            return _error(request_id, -32000, str(result["error"]))
        return _response(request_id, result)

    return _error(request_id, -32601, f"Unknown method: {method}")


async def _handle_tool_call(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    project_manager: ProjectManager,
    code_manager: CodeManager,
    git_manager: GitManager,
    runtime_manager: RuntimeManager,
    test_runner: TestRunner,
    debug_manager: DebugManager,
    deploy_manager: DeployManager,
    test_results: dict[str, TestResultPayload],
    debug_logs: dict[str, list[str]],
) -> dict[str, Any]:
    try:
        project_call = parse_project_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if project_call is not None:
        return await _handle_project_tool_call(project_call, project_manager)

    try:
        code_call = parse_code_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if code_call is not None:
        return await _handle_code_tool_call(code_call, project_manager, code_manager)

    try:
        git_call = parse_git_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if git_call is not None:
        return await _handle_git_tool_call(git_call, project_manager, git_manager)

    try:
        runtime_call = parse_runtime_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if runtime_call is not None:
        return await _handle_runtime_tool_call(
            runtime_call,
            project_manager,
            runtime_manager,
        )

    try:
        test_call = parse_test_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if test_call is not None:
        return await _handle_test_tool_call(
            test_call,
            project_manager,
            test_runner,
            test_results,
        )

    try:
        debug_call = parse_debug_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if debug_call is not None:
        return await _handle_debug_tool_call(debug_call, project_manager, debug_manager, debug_logs)

    try:
        deploy_call = parse_deploy_tool_call(tool_name, arguments)
    except ValueError as exc:
        return {"error": str(exc)}
    if deploy_call is not None:
        return await _handle_deploy_tool_call(deploy_call, project_manager, deploy_manager)

    return {"error": f"Tool handler not implemented: {tool_name}"}


async def _handle_project_tool_call(
    call: ProjectToolCall,
    project_manager: ProjectManager,
) -> dict[str, Any]:
    if call.operation == "list":
        projects = await project_manager.list()
        return {
            "items": [
                {
                    "id": project.id,
                    "name": project.name,
                    "path": str(project.path),
                    "status": project.status.value,
                }
                for project in projects
            ]
        }

    if call.operation == "status":
        if call.project_id is None:
            return {"error": "project_id is required"}
        project = await project_manager.get(call.project_id)
        return {
            "exists": project is not None,
            "status": project.status.value if project else "missing",
        }

    if call.operation == "create":
        if call.name is None or call.path is None:
            return {"error": "name and path are required"}
        create_input = CreateProjectInput(
            name=call.name,
            path=call.path,
            git_remote=call.git_remote,
            nat_config_path=call.nat_config_path,
        )
        if call.clone_from_remote:
            project = await project_manager.clone(create_input)
        else:
            project = await project_manager.create(create_input)
        return {"id": project.id, "status": project.status.value}

    if call.operation == "delete":
        if call.project_id is None:
            return {"error": "project_id is required"}
        await project_manager.delete(call.project_id)
        return {"status": "deleted"}

    if call.operation == "download":
        if call.project_id is None:
            return {"error": "project_id is required"}
        archive_path = await project_manager.download(call.project_id)
        return {"archive_path": str(archive_path)}

    return {"error": f"Project tool operation not implemented: {call.operation}"}


async def _handle_code_tool_call(
    call: CodeToolCall,
    project_manager: ProjectManager,
    code_manager: CodeManager,
) -> dict[str, Any]:
    if call.operation == "diff":
        if call.original is None or call.updated is None:
            return {"error": "original and updated are required"}
        return {
            "diff": code_manager.diff(
                call.original,
                call.updated,
                from_name=call.from_name,
                to_name=call.to_name,
            )
        }

    if call.project_id is None:
        return {"error": "project_id is required"}
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}

    if call.operation == "list":
        return {
            "files": [
                str(path.relative_to(project.path))
                for path in code_manager.list_files(project.path)
            ]
        }

    if call.operation == "read":
        if call.path is None:
            return {"error": "path is required"}
        return {"content": code_manager.read_file(project.path, call.path)}

    if call.operation == "write":
        if call.path is None or call.content is None:
            return {"error": "path and content are required"}
        code_manager.write_file(project.path, call.path, call.content)
        return {"status": "updated"}

    if call.operation == "search":
        if call.pattern is None:
            return {"error": "pattern is required"}
        return {
            "matches": [
                str(path.relative_to(project.path))
                for path in code_manager.search(project.path, call.pattern)
            ]
        }

    return {"error": f"Code tool operation not implemented: {call.operation}"}


async def _handle_git_tool_call(
    call: GitToolCall,
    project_manager: ProjectManager,
    git_manager: GitManager,
) -> dict[str, Any]:
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}

    if call.operation == "status":
        return {"status": git_manager.status(project.path).output}

    if call.operation == "commit":
        if call.message is None:
            return {"error": "message is required"}
        return {"result": git_manager.commit(project.path, call.message).output}

    if call.operation == "push":
        return {"result": git_manager.push(project.path, call.remote, call.branch).output}

    if call.operation == "branch":
        if call.name is None:
            return {"error": "name is required"}
        return {
            "result": git_manager.branch(project.path, call.name, checkout=call.checkout).output
        }

    if call.operation == "pr_create":
        if call.title is None:
            return {"error": "title is required"}
        return {
            "result": git_manager.pr_create(
                project.path,
                title=call.title,
                body=call.body,
                base=call.base,
                head=call.head,
            ).output
        }

    if call.operation == "pr_merge":
        if call.pull_request is None:
            return {"error": "pull_request is required"}
        return {
            "result": git_manager.pr_merge(
                project.path,
                pull_request=call.pull_request,
                strategy=call.strategy,
            ).output
        }

    if call.operation == "pr_review":
        if call.pull_request is None:
            return {"error": "pull_request is required"}
        return {
            "reviews": git_manager.pr_reviews(project.path, pull_request=call.pull_request).output
        }

    if call.operation == "log":
        limit = call.limit if call.limit is not None else 20
        return {"log": git_manager.log(project.path, limit=limit).output}

    if call.operation == "actions":
        limit = call.limit if call.limit is not None else 10
        return {"actions": git_manager.actions(project.path, limit=limit).output}

    return {"error": f"Git tool operation not implemented: {call.operation}"}


async def _handle_runtime_tool_call(
    call: RuntimeToolCall,
    project_manager: ProjectManager,
    runtime_manager: RuntimeManager,
) -> dict[str, Any]:
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}

    if call.operation == "start":
        if call.config_path is None:
            return {"error": "config_path is required"}
        state = runtime_manager.start(project.path, call.config_path)
        return {"running": state.running, "pid": state.pid}

    if call.operation == "stop":
        state = runtime_manager.stop()
        return {"running": state.running, "pid": state.pid}

    if call.operation == "status":
        probe = runtime_manager.probe_health()
        return {
            "running": probe.running,
            "pid": probe.pid,
            "returncode": probe.returncode,
            "healthy": probe.healthy,
            "health_probe": probe.probe,
            "health_reason": probe.reason,
            "health_checked_at": probe.checked_at.isoformat(),
            "health_http_status": probe.http_status,
            "health_command": probe.command,
        }

    if call.operation == "logs":
        return {"logs": runtime_manager.logs()}

    return {"error": f"Runtime tool operation not implemented: {call.operation}"}


async def _handle_test_tool_call(
    call: MCPTestToolCall,
    project_manager: ProjectManager,
    test_runner: TestRunner,
    test_results: dict[str, TestResultPayload],
) -> dict[str, Any]:
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}

    if call.operation == "run":
        test_result = test_runner.run(
            project.path,
            suite=call.suite,
            markers=call.markers,
            timeout_seconds=call.timeout_seconds,
        )
        payload = test_result.as_payload()
        test_results[call.project_id] = payload
        return payload

    if call.operation == "results":
        return test_results.get(call.project_id, {"status": "no_results"})

    return {"error": f"Test tool operation not implemented: {call.operation}"}


async def _handle_debug_tool_call(
    call: DebugToolCall,
    project_manager: ProjectManager,
    debug_manager: DebugManager,
    debug_logs: dict[str, list[str]],
) -> dict[str, Any]:
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}
    logs = debug_logs.get(call.project_id, [])

    if call.operation == "errors":
        return {"errors": debug_manager.errors(logs)}

    if call.operation == "logs":
        filtered = debug_manager.filter_logs(logs, call.query) if call.query else logs
        return {"logs": filtered}

    return {"error": f"Debug tool operation not implemented: {call.operation}"}


async def _handle_deploy_tool_call(
    call: DeployToolCall,
    project_manager: ProjectManager,
    deploy_manager: DeployManager,
) -> dict[str, Any]:
    project = await project_manager.get(call.project_id)
    if project is None:
        return {"error": "project not found"}

    if call.operation == "build":
        status = deploy_manager.build(project.path)
        return {"built": status.built, "running": status.running, "message": status.message}

    if call.operation == "run":
        if call.config_path is None:
            return {"error": "config_path is required"}
        status = deploy_manager.run(project.path, call.config_path)
        return {"built": status.built, "running": status.running, "message": status.message}

    if call.operation == "status":
        status = deploy_manager.status()
        return {"built": status.built, "running": status.running, "message": status.message}

    return {"error": f"Deploy tool operation not implemented: {call.operation}"}


async def _handle_resource_read(
    *,
    uri: str,
    project_manager: ProjectManager,
    code_manager: CodeManager,
    git_manager: GitManager,
    runtime_manager: RuntimeManager,
    test_results: dict[str, TestResultPayload],
) -> dict[str, Any]:
    resource_ref = parse_resource_ref(uri)
    if resource_ref is None:
        return {"error": f"Unknown resource uri: {uri}"}

    if resource_ref.operation == "projects":
        projects = await project_manager.list()
        return {
            "items": [
                {
                    "id": project.id,
                    "name": project.name,
                    "path": str(project.path),
                    "status": project.status.value,
                }
                for project in projects
            ]
        }

    if resource_ref.project_id is None:
        return {"error": f"Invalid resource uri: {uri}"}
    project_id = resource_ref.project_id

    if resource_ref.operation == "files":
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {
            "files": [
                str(path.relative_to(project.path))
                for path in code_manager.list_files(project.path)
            ]
        }

    if resource_ref.operation == "config":
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        config_path = project.nat_config_path
        if config_path is None:
            return {"error": "project config not set"}
        resolved = config_path if config_path.is_absolute() else project.path / config_path
        if not resolved.exists():
            return {"error": "project config file not found"}
        return {"path": str(resolved), "content": resolved.read_text(encoding="utf-8")}

    if resource_ref.operation == "tests":
        return test_results.get(project_id, {"status": "no_results"})

    if resource_ref.operation == "logs":
        return {"logs": runtime_manager.logs()}

    if resource_ref.operation == "ci":
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"actions": git_manager.actions(project.path).output}

    return {"error": f"Resource operation not implemented: {resource_ref.operation}"}
