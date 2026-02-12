# P12 - mcp_server

## Status
in_progress

## Phase
1.1

## Dependencies
P04-P08,P10

## Scope
- Define concrete implementation tasks.
- Define required tests and acceptance criteria.
- Track delivery notes and unresolved risks.

## Acceptance Criteria
- The implementation is merged with passing CI checks.
- Tests for this plan item exist and cover baseline behavior.
- `todo/master_plan.md` is updated with completion status.

## Notes
- Implemented baseline tool and resource catalog in `src/att/mcp/server.py`.
- Added lookup helper (`find_tool`) and unit coverage in `tests/unit/test_mcp_server.py`.
- Exposed catalog through REST routes in `src/att/api/routes/mcp.py`.
- Catalog is now consumed by invocation routes (`/api/v1/mcp/invoke/*`) for tool/resource discovery-aligned APIs.
- Added MCP Streamable HTTP-style transport endpoint at `POST /mcp` in `src/att/api/routes/mcp_transport.py`.
- Transport now supports handshake methods (`initialize`, `notifications/initialized`, `ping`) and manager-backed tool/resource execution for ATT project/code/git/runtime/test/debug/deploy operations.
- Implemented project archive support in transport via `att.project.download`.
- Added typed project-tool adapter parsing in `src/att/mcp/tools/project_tools.py` and integrated it into transport project operations.
- Added typed code-tool adapter parsing in `src/att/mcp/tools/code_tools.py` and integrated it into transport code operations.
- Added typed git-tool adapter parsing in `src/att/mcp/tools/git_tools.py` and integrated it into transport git operations.
- Added typed runtime/test tool adapter parsing in `src/att/mcp/tools/runtime_tools.py` and `src/att/mcp/tools/test_tools.py`, integrated into transport runtime/test operations.
- Extended typed test-tool parsing with optional `markers` and `timeout_seconds` arguments for `att.test.run`.
- Added typed debug/deploy tool adapter parsing in `src/att/mcp/tools/debug_tools.py` and `src/att/mcp/tools/deploy_tools.py`, integrated into transport debug/deploy operations.
- Added typed resource URI parsing in `src/att/mcp/tools/resource_refs.py` and integrated it into transport `resources/read` dispatch.
- Aligned runtime log access across MCP tool/resource surfaces so `att.runtime.logs` and `att://project/{id}/logs` both read from `RuntimeManager.logs()`.
- Added defensive JSON-RPC error wrapping so unexpected handler exceptions return MCP error payloads instead of raw 500s.
- Test operation responses now surface richer runner summaries (counts, duration, timeout/no-tests flags) via MCP transport.
- Added transport integration coverage in `tests/integration/test_mcp_transport.py` and adapter unit coverage in `tests/unit/test_project_tools.py` + `tests/unit/test_code_tools.py` + `tests/unit/test_git_tools.py` + `tests/unit/test_runtime_tools.py` + `tests/unit/test_test_tools.py` + `tests/unit/test_debug_tools.py` + `tests/unit/test_deploy_tools.py` + `tests/unit/test_resource_refs.py`.
