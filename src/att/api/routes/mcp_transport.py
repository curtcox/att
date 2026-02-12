"""MCP JSON-RPC transport endpoint."""

from __future__ import annotations

import re
from pathlib import Path
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
from att.core.test_runner import TestRunner
from att.mcp.server import find_tool, registered_resources, registered_tools

router = APIRouter(tags=["mcp-transport"])

_PROJECT_FILES_URI = re.compile(r"^att://project/([^/]+)/files$")
_PROJECT_CONFIG_URI = re.compile(r"^att://project/([^/]+)/config$")
_PROJECT_TESTS_URI = re.compile(r"^att://project/([^/]+)/tests$")
_PROJECT_LOGS_URI = re.compile(r"^att://project/([^/]+)/logs$")
_PROJECT_CI_URI = re.compile(r"^att://project/([^/]+)/ci$")


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


def _parse_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return default


def _parse_int(value: Any, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


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
    test_results: dict[str, dict[str, str | int]] = Depends(get_test_result_store),
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
        if isinstance(result, dict) and "error" in result:
            return _error(request_id, -32000, str(result["error"]))
        return _response(request_id, result)

    if method == "resources/read":
        uri = params.get("uri")
        if not isinstance(uri, str):
            return _error(request_id, -32602, "Missing resource uri")
        result = await _handle_resource_read(
            uri=uri,
            project_manager=project_manager,
            code_manager=code_manager,
            git_manager=git_manager,
            test_results=test_results,
            debug_logs=debug_logs,
        )
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
    test_results: dict[str, dict[str, str | int]],
    debug_logs: dict[str, list[str]],
) -> dict[str, Any]:
    if tool_name == "att.project.list":
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

    if tool_name == "att.project.status":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        return {
            "exists": project is not None,
            "status": project.status.value if project else "missing",
        }

    if tool_name == "att.project.create":
        name = str(arguments.get("name", ""))
        path = str(arguments.get("path", ""))
        if not name or not path:
            return {"error": "name and path are required"}
        project = await project_manager.create(CreateProjectInput(name=name, path=Path(path)))
        return {"id": project.id}

    if tool_name == "att.project.delete":
        project_id = str(arguments.get("project_id", ""))
        if not project_id:
            return {"error": "project_id is required"}
        await project_manager.delete(project_id)
        return {"status": "deleted"}

    if tool_name == "att.project.download":
        return {"error": "att.project.download is not yet implemented"}

    if tool_name == "att.code.list":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {
            "files": [
                str(path.relative_to(project.path))
                for path in code_manager.list_files(project.path)
            ]
        }

    if tool_name == "att.code.read":
        project_id = str(arguments.get("project_id", ""))
        file_path = str(arguments.get("path", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"content": code_manager.read_file(project.path, file_path)}

    if tool_name == "att.code.write":
        project_id = str(arguments.get("project_id", ""))
        file_path = str(arguments.get("path", ""))
        content = str(arguments.get("content", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        code_manager.write_file(project.path, file_path, content)
        return {"status": "updated"}

    if tool_name == "att.code.search":
        project_id = str(arguments.get("project_id", ""))
        pattern = str(arguments.get("pattern", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {
            "matches": [
                str(path.relative_to(project.path))
                for path in code_manager.search(project.path, pattern)
            ]
        }

    if tool_name == "att.code.diff":
        original = str(arguments.get("original", ""))
        updated = str(arguments.get("updated", ""))
        from_name = str(arguments.get("from_name", "original"))
        to_name = str(arguments.get("to_name", "updated"))
        return {"diff": code_manager.diff(original, updated, from_name=from_name, to_name=to_name)}

    if tool_name == "att.git.status":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"status": git_manager.status(project.path).output}

    if tool_name == "att.git.commit":
        project_id = str(arguments.get("project_id", ""))
        message = str(arguments.get("message", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not message:
            return {"error": "message is required"}
        return {"result": git_manager.commit(project.path, message).output}

    if tool_name == "att.git.push":
        project_id = str(arguments.get("project_id", ""))
        remote = str(arguments.get("remote", "origin"))
        branch = str(arguments.get("branch", "HEAD"))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"result": git_manager.push(project.path, remote, branch).output}

    if tool_name == "att.git.branch":
        project_id = str(arguments.get("project_id", ""))
        name = str(arguments.get("name", ""))
        checkout = _parse_bool(arguments.get("checkout"), default=True)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not name:
            return {"error": "name is required"}
        return {"result": git_manager.branch(project.path, name, checkout=checkout).output}

    if tool_name == "att.git.pr.create":
        project_id = str(arguments.get("project_id", ""))
        title = str(arguments.get("title", ""))
        body = str(arguments.get("body", ""))
        base = str(arguments.get("base", "dev"))
        head = arguments.get("head")
        if head is not None:
            head = str(head)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not title:
            return {"error": "title is required"}
        return {
            "result": git_manager.pr_create(
                project.path,
                title=title,
                body=body,
                base=base,
                head=head,
            ).output
        }

    if tool_name == "att.git.pr.merge":
        project_id = str(arguments.get("project_id", ""))
        pull_request = str(arguments.get("pull_request", ""))
        strategy = str(arguments.get("strategy", "squash"))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not pull_request:
            return {"error": "pull_request is required"}
        return {
            "result": git_manager.pr_merge(
                project.path,
                pull_request=pull_request,
                strategy=strategy,
            ).output
        }

    if tool_name == "att.git.pr.review":
        project_id = str(arguments.get("project_id", ""))
        pull_request = str(arguments.get("pull_request", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not pull_request:
            return {"error": "pull_request is required"}
        return {"reviews": git_manager.pr_reviews(project.path, pull_request=pull_request).output}

    if tool_name == "att.git.log":
        project_id = str(arguments.get("project_id", ""))
        limit = _parse_int(arguments.get("limit"), default=20)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"log": git_manager.log(project.path, limit=limit).output}

    if tool_name == "att.git.actions":
        project_id = str(arguments.get("project_id", ""))
        limit = _parse_int(arguments.get("limit"), default=10)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"actions": git_manager.actions(project.path, limit=limit).output}

    if tool_name == "att.runtime.start":
        project_id = str(arguments.get("project_id", ""))
        config_path = str(arguments.get("config_path", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not config_path:
            return {"error": "config_path is required"}
        state = runtime_manager.start(project.path, Path(config_path))
        return {"running": state.running, "pid": state.pid}

    if tool_name == "att.runtime.stop":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        state = runtime_manager.stop()
        return {"running": state.running, "pid": state.pid}

    if tool_name == "att.runtime.status":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        state = runtime_manager.status()
        return {"running": state.running, "pid": state.pid}

    if tool_name == "att.runtime.logs":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"logs": debug_logs.get(project_id, [])}

    if tool_name == "att.test.run":
        project_id = str(arguments.get("project_id", ""))
        suite = str(arguments.get("suite", "unit"))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        test_result = test_runner.run(project.path, suite=suite)
        payload: dict[str, str | int] = {
            "command": test_result.command,
            "returncode": test_result.returncode,
            "output": test_result.output,
        }
        test_results[project_id] = payload
        return payload

    if tool_name == "att.test.results":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return test_results.get(project_id, {"status": "no_results"})

    if tool_name == "att.debug.errors":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        logs = debug_logs.get(project_id, [])
        return {"errors": debug_manager.errors(logs)}

    if tool_name == "att.debug.logs":
        project_id = str(arguments.get("project_id", ""))
        query = str(arguments.get("query", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        logs = debug_logs.get(project_id, [])
        filtered = debug_manager.filter_logs(logs, query) if query else logs
        return {"logs": filtered}

    if tool_name == "att.deploy.build":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        status = deploy_manager.build(project.path)
        return {"built": status.built, "running": status.running, "message": status.message}

    if tool_name == "att.deploy.run":
        project_id = str(arguments.get("project_id", ""))
        config_path = str(arguments.get("config_path", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        if not config_path:
            return {"error": "config_path is required"}
        status = deploy_manager.run(project.path, Path(config_path))
        return {"built": status.built, "running": status.running, "message": status.message}

    if tool_name == "att.deploy.status":
        project_id = str(arguments.get("project_id", ""))
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        status = deploy_manager.status()
        return {"built": status.built, "running": status.running, "message": status.message}

    return {"error": f"Tool handler not implemented: {tool_name}"}


async def _handle_resource_read(
    *,
    uri: str,
    project_manager: ProjectManager,
    code_manager: CodeManager,
    git_manager: GitManager,
    test_results: dict[str, dict[str, str | int]],
    debug_logs: dict[str, list[str]],
) -> dict[str, Any]:
    if uri == "att://projects":
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

    files_match = _PROJECT_FILES_URI.match(uri)
    if files_match:
        project_id = files_match.group(1)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {
            "files": [
                str(path.relative_to(project.path))
                for path in code_manager.list_files(project.path)
            ]
        }

    config_match = _PROJECT_CONFIG_URI.match(uri)
    if config_match:
        project_id = config_match.group(1)
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

    tests_match = _PROJECT_TESTS_URI.match(uri)
    if tests_match:
        project_id = tests_match.group(1)
        return test_results.get(project_id, {"status": "no_results"})

    logs_match = _PROJECT_LOGS_URI.match(uri)
    if logs_match:
        project_id = logs_match.group(1)
        return {"logs": debug_logs.get(project_id, [])}

    ci_match = _PROJECT_CI_URI.match(uri)
    if ci_match:
        project_id = ci_match.group(1)
        project = await project_manager.get(project_id)
        if project is None:
            return {"error": "project not found"}
        return {"actions": git_manager.actions(project.path).output}

    return {"error": f"Unknown resource uri: {uri}"}
