# Next Machine Handoff

## Snapshot
- Date: 2026-02-13
- Branch: `main`
- HEAD: `1d4fc8d767b34031caee6e3ede14769f22b1fd2b`
- Last commit: `1d4fc8d 2026-02-12 17:46:16 -0600 Refine test result payload typing`
- Working tree at handoff creation: dirty (self-bootstrap release-source/policy-matrix hardening + plan doc updates)
- Validation status:
  - `./.venv313/bin/python --version` => `Python 3.13.12`
  - `./.venv313/bin/ruff format .` passes
  - `./.venv313/bin/ruff check .` passes
  - `PYTHONPATH=src ./.venv313/bin/mypy` passes
  - `PYTHONPATH=src ./.venv313/bin/pytest` passes (`128 passed`)

## Recent Delivered Work
- Self-bootstrap release source abstraction delivered:
  - added `ReleaseSourceContext` + `ReleaseSourceAdapter` contract in `SelfBootstrapManager`
  - added fallback-chain resolution support while preserving compatibility with legacy `release_metadata_provider` hooks
- Source-of-truth fallback chain wired in API deps:
  - runtime-log adapter scans for `release_id` / `previous_release_id`
  - git adapter fallback (`HEAD`, `HEAD^`)
- Rollback policy matrix hardened by failure class + deployment context:
  - failure classes enforced: `deploy_failure`, `restart_watchdog_failure`, `health_failure`
  - explicit request controls added: `rollback_on_deploy_failure`, `rollback_on_restart_watchdog_failure`, `rollback_on_health_failure`
  - deployment context added: `deployment_context` (`self_hosted`/`external`)
  - policy deny path for external context without explicit rollback target: `rollback_target_required_for_external_context`
- Self-bootstrap result/API payload expanded with policy diagnostics:
  - `rollback_failure_class`
  - `rollback_deployment_context`
- API route/schema wiring updated for new request+response policy fields.
- Test coverage expanded:
  - new unit tests for adapter fallback chain and policy matrix branches
  - integration route test verifies new request field passthrough + response fields

## Active Next Slice (Recommended)
Focus next on `P12/P13` transport hardening for real multi-server MCP operations:
1. Drive `nat.mcp` external-server connect/invoke flows through live transport behavior (beyond in-memory baseline assumptions).
2. Expand failover/recovery semantics for mixed server health and partial initialization states.

Suggested implementation direction:
- Strengthen `MCPClientManager` server lifecycle transitions with explicit per-server capability snapshots.
- Add integration tests for connect/initialize/invoke sequencing with degraded and recovering peers.
- Tighten API error mapping for partial-failure multi-server calls (deterministic status + payload shape).

## Resume Checklist
1. Sync and verify environment:
   - `git pull`
   - `./.venv313/bin/python --version`
2. Read context docs:
   - `todo/master_plan.md`
   - `todo/plans/mcp_server.md`
   - `todo/plans/mcp_client.md`
3. Implement one slice end-to-end (code + tests + plan updates).
4. Run validation:
   - `./.venv313/bin/ruff format .`
   - `./.venv313/bin/ruff check .`
   - `PYTHONPATH=src ./.venv313/bin/mypy`
   - `PYTHONPATH=src ./.venv313/bin/pytest`
5. Record new state back into this file and `todo/master_plan.md`.

## Key Files for Next Slice
- `src/att/mcp/client.py`
- `src/att/mcp/server.py`
- `src/att/api/routes/mcp.py`
- `src/att/api/routes/mcp_transport.py`
- `tests/unit/test_mcp_client.py`
- `tests/integration/test_api_mcp.py`
- `tests/integration/test_mcp_transport.py`

## Remaining Program-Level Milestones
From `todo/master_plan.md`:
- `P12/P13` still in progress for full NAT `nat.mcp` transport integration and live external server wiring.
- `P16` still in progress (release-source adapter chain + failure-class/deployment-context rollback policy matrix delivered; remaining work is deeper production rollout hardening).
- `P15` and `P17-P25` not started.

## Working Agreement
- Keep edits small, test-backed, and incremental.
- Update plan files as work progresses, not only at the end.
- If blocked, record blocker + attempted approach in this file before stopping.
