"""Shared API dependency providers."""

from __future__ import annotations

from pathlib import Path

from att.core.code_manager import CodeManager
from att.core.debug_manager import DebugManager
from att.core.deploy_manager import DeployManager
from att.core.git_manager import GitManager
from att.core.project_manager import ProjectManager
from att.core.runtime_manager import RuntimeManager
from att.core.test_runner import TestRunner
from att.db.store import SQLiteStore
from att.mcp.client import MCPClientManager

APP_DB_PATH = Path(".att/att.db")
_RUNTIME_MANAGER = RuntimeManager()
_CODE_MANAGER = CodeManager()
_GIT_MANAGER = GitManager()
_TEST_RUNNER = TestRunner()
_DEBUG_MANAGER = DebugManager()
_DEPLOY_MANAGER = DeployManager(_RUNTIME_MANAGER)
_MCP_CLIENT_MANAGER = MCPClientManager()
_TEST_RESULTS: dict[str, dict[str, str | int]] = {}
_DEBUG_LOGS: dict[str, list[str]] = {}


def get_store() -> SQLiteStore:
    APP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStore(db_path=APP_DB_PATH)


def get_project_manager() -> ProjectManager:
    return ProjectManager(store=get_store())


def get_code_manager() -> CodeManager:
    return _CODE_MANAGER


def get_git_manager() -> GitManager:
    return _GIT_MANAGER


def get_runtime_manager() -> RuntimeManager:
    return _RUNTIME_MANAGER


def get_test_runner() -> TestRunner:
    return _TEST_RUNNER


def get_debug_manager() -> DebugManager:
    return _DEBUG_MANAGER


def get_deploy_manager() -> DeployManager:
    return _DEPLOY_MANAGER


def get_mcp_client_manager() -> MCPClientManager:
    return _MCP_CLIENT_MANAGER


def get_test_result_store() -> dict[str, dict[str, str | int]]:
    return _TEST_RESULTS


def get_debug_log_store() -> dict[str, list[str]]:
    return _DEBUG_LOGS
