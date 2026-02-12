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
- Added defensive JSON-RPC error wrapping so unexpected handler exceptions return MCP error payloads instead of raw 500s.
- Added transport integration coverage in `tests/integration/test_mcp_transport.py` and adapter unit coverage in `tests/unit/test_project_tools.py` + `tests/unit/test_code_tools.py` + `tests/unit/test_git_tools.py`.
