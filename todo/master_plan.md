# ATT (Agent Toolkit Toolkit) Master Plan

## Vision

ATT is a web-based application for developing, running, debugging, and deploying NVIDIA NeMo Agent Toolkit (NAT) apps. It is built on NAT itself, exposes an OpenAPI interface, and functions as both an MCP client and MCP server. The top priority is reaching self-bootstrapping: the point where ATT can create future versions of itself.

## Reference Technologies

- [NVIDIA NeMo Agent Toolkit](https://developer.nvidia.com/nemo-agent-toolkit) — core framework (FastAPI frontend, YAML-driven workflows, MCP/A2A support)
- [NeMo Agent Toolkit UI](https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI) — Next.js reference UI (proxy architecture, WebSocket, HITL workflows)
- [MCP UI](https://mcpui.dev/) — sandboxed iframe UI rendering for MCP tools, multi-SDK
- [OpenAI Apps SDK](https://developers.openai.com/apps-sdk/) — MCP-server-based apps with native UI, discovery, deployment pipeline
- [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25) — JSON-RPC protocol, tools/resources/prompts/roots, Streamable HTTP transport

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ATT Web UI                           │
│   (NAT FastAPI Frontend + NAT-UI components)            │
│   Project Manager │ Code Editor │ Terminal │ Logs │ Chat│
├────────────────────────┬────────────────────────────────┤
│   ATT API Server       │     MCP Server (Streamable HTTP)│
│   (FastAPI/OpenAPI)    │     Tools: project, code, git,  │
│   REST + WebSocket     │     ci, deploy, debug, test     │
├────────────────────────┴────────────────────────────────┤
│                ATT Core Engine                          │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐│
│   │ Project  │ │ Code     │ │ Git/CI   │ │ Runtime   ││
│   │ Manager  │ │ Manager  │ │ Manager  │ │ Manager   ││
│   └──────────┘ └──────────┘ └──────────┘ └───────────┘│
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐│
│   │ Test     │ │ Debug    │ │ Deploy   │ │ Tool      ││
│   │ Runner   │ │ Manager  │ │ Manager  │ │ Orchestr. ││
│   └──────────┘ └──────────┘ └──────────┘ └───────────┘│
├─────────────────────────────────────────────────────────┤
│                  MCP Client Layer                       │
│   Connects to: Claude Code, Codex, Windsurf, GitHub,   │
│   filesystem, terminal, NAT profiler, external MCP svrs│
├─────────────────────────────────────────────────────────┤
│                  NAT Runtime                            │
│   nat serve │ YAML configs │ workflow engine │ profiler │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, NAT (`nvidia-nat`) |
| Frontend | NAT FastAPI Frontend + NAT-UI (Next.js/React/TypeScript) |
| Protocol | MCP (JSON-RPC 2.0, Streamable HTTP), OpenAPI 3.1 |
| Database | SQLite (local), PostgreSQL (cloud) |
| Queue | Redis (optional, for async jobs) |
| Package Manager | `uv` (Astral) |
| Testing | pytest, hypothesis, playwright, mypy, ruff |
| CI/CD | GitHub Actions (tiered) |
| Containers | Docker / Docker Compose (optional) |
| Deployment | Local-first, cloud migration path via Docker/K8s |

---

## Phase Plan

### Phase 0: Foundation (self-bootstrapping prerequisite)
**Goal**: Skeleton project with CI, core managers, and basic web UI.

### Phase 1: Self-Bootstrapping MVP
**Goal**: ATT can edit its own code, run its own tests, create PRs, and merge changes.

### Phase 2: Full NAT App Development
**Goal**: Users can create, run, debug, and deploy arbitrary NAT apps through the web UI.

### Phase 3: Cloud & Production Hardening
**Goal**: Cloud deployment, multi-user, security, observability.

---

## Phase 0: Foundation

### 0.1 Project Skeleton
- Initialize Python project with `uv` and `pyproject.toml`
- Directory structure:

```
att/
├── src/
│   └── att/
│       ├── __init__.py
│       ├── core/                  # Core engine modules
│       │   ├── __init__.py
│       │   ├── project_manager.py
│       │   ├── code_manager.py
│       │   ├── git_manager.py
│       │   ├── runtime_manager.py
│       │   ├── test_runner.py
│       │   ├── debug_manager.py
│       │   ├── deploy_manager.py
│       │   └── tool_orchestrator.py
│       ├── api/                   # FastAPI routes + OpenAPI
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── routes/
│       │   └── schemas/
│       ├── mcp/                   # MCP server + client
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── client.py
│       │   └── tools/
│       ├── nat_integration/       # NAT workflow configs + plugins
│       │   ├── __init__.py
│       │   ├── configs/
│       │   └── workflows/
│       └── models/                # Data models
│           ├── __init__.py
│           ├── project.py
│           └── events.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   └── e2e/
├── configs/                       # NAT YAML configs for ATT itself
├── external/
│   └── nat-ui/                    # NAT-UI submodule
├── .github/
│   └── workflows/
│       ├── pr-quick.yml           # Tier 1: fast PR checks
│       └── main-full.yml          # Tier 2: full pre-merge
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

- Dependencies: `nvidia-nat`, `fastapi`, `uvicorn`, `mcp` (Python SDK), `httpx`, `pydantic`
- Dev dependencies: `pytest`, `pytest-asyncio`, `hypothesis`, `playwright`, `mypy`, `ruff`, `coverage`, `pytest-cov`

### 0.2 CI/CD — Tiered GitHub Actions

**Tier 1: PR Quick Checks** (`pr-quick.yml` — runs on PR to `dev`)
- Trigger: `pull_request` targeting `dev`
- Steps:
  1. Lint with `ruff check` and `ruff format --check` (~5s)
  2. Type check with `mypy --strict` (~10s)
  3. Unit tests with `pytest tests/unit/ -x --timeout=30` (~15s)
  4. Property tests with `pytest tests/property/ -x --timeout=60` (~30s)
  5. Coverage gate: fail if < 80%
- Target: < 2 minutes total

**Tier 2: Full Pre-Merge** (`main-full.yml` — runs on PR to `main`)
- Trigger: `pull_request` targeting `main`
- Steps:
  1. Everything from Tier 1
  2. Integration tests: `pytest tests/integration/ --timeout=120` (~2min)
  3. E2E tests: `pytest tests/e2e/ --timeout=300` (~5min)
  4. Security scan: `bandit -r src/`
  5. Dependency audit: `pip-audit`
  6. Build Docker image
  7. Smoke test Docker image (start server, hit health endpoint)
- Target: < 10 minutes total

### 0.3 Core Data Models

```python
# project.py
class Project(BaseModel):
    id: str
    name: str
    path: Path
    git_remote: str | None
    nat_config_path: Path
    status: ProjectStatus  # created | cloned | running | stopped | error
    created_at: datetime
    updated_at: datetime

class ProjectStatus(str, Enum):
    CREATED = "created"
    CLONED = "cloned"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

# events.py
class ATTEvent(BaseModel):
    id: str
    project_id: str
    event_type: EventType
    payload: dict
    timestamp: datetime

class EventType(str, Enum):
    PROJECT_CREATED = "project.created"
    CODE_CHANGED = "code.changed"
    TEST_RUN = "test.run"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    DEPLOY_STARTED = "deploy.started"
    DEPLOY_COMPLETED = "deploy.completed"
    GIT_COMMIT = "git.commit"
    GIT_PR_CREATED = "git.pr.created"
    GIT_PR_MERGED = "git.pr.merged"
    ERROR = "error"
```

### 0.4 Core Managers (interfaces first, TDD)

Each manager is developed interface-first with tests written before implementation.

**ProjectManager** — create, list, clone, delete projects
**CodeManager** — read, write, search, diff files within a project
**GitManager** — status, add, commit, push, branch, PR, merge, log, diff
**RuntimeManager** — start (`nat serve`), stop, restart, status, logs
**TestRunner** — run unit/integration/e2e tests, parse results, report
**DebugManager** — read logs, read errors, fetch stack traces, attach profiler
**DeployManager** — build, push image, deploy (local Docker or remote)
**ToolOrchestrator** — coordinate multi-step workflows across managers

---

## Phase 1: Self-Bootstrapping MVP

### 1.1 MCP Server — Expose ATT Tools
Expose each manager operation as an MCP tool via Streamable HTTP transport:

| Tool Name | Description |
|-----------|-------------|
| `att.project.create` | Create a new NAT project from template |
| `att.project.list` | List all projects |
| `att.project.status` | Get project status |
| `att.code.read` | Read file contents |
| `att.code.write` | Write/update file contents |
| `att.code.search` | Search across project files |
| `att.code.diff` | Show diff of changes |
| `att.git.status` | Git status of project |
| `att.git.commit` | Stage and commit changes |
| `att.git.push` | Push to remote |
| `att.git.branch` | Create/switch branches |
| `att.git.pr.create` | Create pull request |
| `att.git.pr.merge` | Merge pull request |
| `att.git.pr.review` | Get PR review comments |
| `att.git.log` | Git log |
| `att.git.actions` | Get GitHub Actions status/logs |
| `att.runtime.start` | Start NAT workflow server |
| `att.runtime.stop` | Stop NAT workflow server |
| `att.runtime.logs` | Get runtime logs |
| `att.runtime.status` | Get runtime status |
| `att.test.run` | Run test suite (unit/integration/e2e) |
| `att.test.results` | Get test results |
| `att.debug.errors` | Get current errors/stack traces |
| `att.debug.logs` | Get filtered debug logs |
| `att.deploy.build` | Build deployment artifact |
| `att.deploy.push` | Push to registry |
| `att.deploy.run` | Deploy to target |

MCP Resources:
| Resource URI | Description |
|-------------|-------------|
| `att://projects` | List of all projects |
| `att://project/{id}/files` | File tree for project |
| `att://project/{id}/config` | NAT YAML config |
| `att://project/{id}/tests` | Latest test results |
| `att://project/{id}/logs` | Runtime logs |
| `att://project/{id}/ci` | CI pipeline status |

### 1.2 MCP Client — Connect to External Tools
Connect to external MCP servers for enhanced capabilities:

| External Server | Purpose |
|----------------|---------|
| Claude Code MCP | AI-assisted code editing, review, explanation |
| GitHub MCP | Issues, PRs, actions, code search |
| Filesystem MCP | Direct file access |
| Terminal MCP | Shell command execution |
| Windsurf/Codex | Alternative AI code assistants |

The MCP client uses dynamic server discovery and configuration stored per-project.

### 1.3 OpenAPI Interface
All REST endpoints auto-generate OpenAPI 3.1 spec via FastAPI:

```
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
DELETE /api/v1/projects/{id}
GET    /api/v1/projects/{id}/files
GET    /api/v1/projects/{id}/files/{path}
PUT    /api/v1/projects/{id}/files/{path}
POST   /api/v1/projects/{id}/git/commit
POST   /api/v1/projects/{id}/git/push
POST   /api/v1/projects/{id}/git/branch
POST   /api/v1/projects/{id}/git/pr
GET    /api/v1/projects/{id}/git/status
GET    /api/v1/projects/{id}/git/log
GET    /api/v1/projects/{id}/git/actions
POST   /api/v1/projects/{id}/runtime/start
POST   /api/v1/projects/{id}/runtime/stop
GET    /api/v1/projects/{id}/runtime/status
GET    /api/v1/projects/{id}/runtime/logs
POST   /api/v1/projects/{id}/test/run
GET    /api/v1/projects/{id}/test/results
GET    /api/v1/projects/{id}/debug/errors
GET    /api/v1/projects/{id}/debug/logs
POST   /api/v1/projects/{id}/deploy/build
POST   /api/v1/projects/{id}/deploy/push
POST   /api/v1/projects/{id}/deploy/run
WS     /api/v1/projects/{id}/ws             # WebSocket for streaming
GET    /api/v1/health
GET    /api/v1/mcp/.well-known              # MCP discovery
```

### 1.4 Web UI — NAT Frontend Integration
Build on the NAT FastAPI Frontend + NAT-UI:

**Views:**
1. **Dashboard** — project list, status overview, quick actions
2. **Project View** — file tree, code editor (Monaco/CodeMirror), terminal, logs
3. **Git View** — branch visualization, diff viewer, PR management
4. **Test View** — test results, coverage reports, failure details
5. **Runtime View** — server status, log streaming, health metrics
6. **Deploy View** — build status, deployment targets, deployment history
7. **Chat View** — NAT-style chat with ATT agent for natural language interaction
8. **Settings** — MCP server connections, tool configuration, project templates

### 1.5 Self-Bootstrap Capability
The critical milestone — ATT operating on its own codebase:

1. ATT registers itself as a project (pointing to its own repo)
2. User (or AI agent via MCP/chat) requests a change
3. ATT creates a branch via GitManager
4. ATT edits its own source via CodeManager
5. ATT runs its own tests via TestRunner
6. ATT creates a PR via GitManager
7. CI runs (GitHub Actions Tier 1)
8. On CI pass, ATT merges the PR
9. ATT rebuilds and redeploys itself via DeployManager
10. Health check confirms new version is running

---

## Phase 2: Full NAT App Development

### 2.1 Project Templates
- Starter templates for common NAT app patterns (chatbot, RAG, multi-agent, tool-server)
- Template registry with versioning
- `nat init`-style project scaffolding through the UI

### 2.2 NAT Config Editor
- Visual YAML config editor with validation
- Component browser (LLMs, tools, workflows)
- Live preview of workflow graph

### 2.3 Tool Marketplace / MCP Registry
- Browse and connect to MCP servers from registry
- Publish ATT-created tools as MCP servers
- A2A agent discovery and connection

### 2.4 Advanced Debugging
- NAT profiler integration (token usage, latency, cost)
- Execution trace visualization
- Breakpoint-style step-through for agent workflows
- Live log filtering and search

### 2.5 Deployment Pipelines
- One-click deploy to Docker/K8s
- Environment management (dev/staging/prod)
- Rollback support
- Blue/green deployments

---

## Phase 3: Cloud & Production Hardening

### 3.1 Multi-User Support
- Authentication (OAuth 2.0 / API keys)
- Per-user project isolation
- Role-based access control

### 3.2 Cloud Deployment
- PostgreSQL for persistent storage
- Redis for job queues and caching
- Kubernetes manifests / Helm charts
- Cloud provider integrations (AWS, GCP, Azure)

### 3.3 Observability
- OpenTelemetry integration
- Structured logging (JSON)
- Metrics dashboard
- Alerting rules

### 3.4 Security
- Input sanitization on all endpoints
- Sandboxed code execution for managed projects
- Secret management (no plaintext secrets in configs)
- Dependency vulnerability scanning
- Rate limiting

---

## Detailed Sub-Plans Required

Each sub-plan will be a separate document in `todo/plans/` with full specifications, tests, and acceptance criteria.

| # | Sub-Plan | Dependencies | Phase |
|---|----------|-------------|-------|
| P01 | `project_skeleton.md` — uv setup, pyproject.toml, directory structure, dev tooling | None | 0.1 |
| P02 | `ci_github_actions.md` — Tier 1 + Tier 2 workflow definitions, matrix strategy | P01 | 0.2 |
| P03 | `data_models.md` — Pydantic models, database schema, migrations | P01 | 0.3 |
| P04 | `project_manager.md` — CRUD, template instantiation, project lifecycle | P03 | 0.4 |
| P05 | `code_manager.md` — file read/write/search/diff, working directory isolation | P03 | 0.4 |
| P06 | `git_manager.md` — all git operations, GitHub API integration | P03 | 0.4 |
| P07 | `runtime_manager.md` — nat serve lifecycle, log capture, health checks | P03, P04 | 0.4 |
| P08 | `test_runner.md` — test execution, result parsing, coverage reporting | P03, P05 | 0.4 |
| P09 | `debug_manager.md` — error collection, log filtering, profiler integration | P03, P07 | 0.4 |
| P10 | `deploy_manager.md` — Docker build, push, run, health verification | P03, P07 | 0.4 |
| P11 | `tool_orchestrator.md` — multi-step workflow coordination, event bus | P04-P10 | 0.4 |
| P12 | `mcp_server.md` — tool registration, Streamable HTTP transport, auth | P04-P10 | 1.1 |
| P13 | `mcp_client.md` — server discovery, connection management, tool invocation | P11 | 1.2 |
| P14 | `openapi_routes.md` — REST endpoints, request validation, error handling | P04-P10 | 1.3 |
| P15 | `web_ui.md` — NAT-UI integration, views, WebSocket streaming | P14 | 1.4 |
| P16 | `self_bootstrap.md` — self-modification workflow, safety rails, rollback | P04-P13 | 1.5 |
| P17 | `project_templates.md` — template system, registry, scaffolding | P04 | 2.1 |
| P18 | `nat_config_editor.md` — visual YAML editor, component browser | P15 | 2.2 |
| P19 | `mcp_registry.md` — marketplace, discovery, publishing | P12, P13 | 2.3 |
| P20 | `advanced_debugging.md` — profiler UI, execution traces, breakpoints | P09, P15 | 2.4 |
| P21 | `deploy_pipelines.md` — multi-env, rollback, blue/green | P10, P15 | 2.5 |
| P22 | `multi_user.md` — auth, isolation, RBAC | P14 | 3.1 |
| P23 | `cloud_deploy.md` — PostgreSQL, Redis, K8s, Helm | P10, P22 | 3.2 |
| P24 | `observability.md` — OpenTelemetry, metrics, alerting | P14 | 3.3 |
| P25 | `security_hardening.md` — sandboxing, secrets, scanning, rate limiting | P14, P22 | 3.4 |

### Dependency Graph (Critical Path to Self-Bootstrapping)

```
P01 → P02
P01 → P03 → P04 → P07 → P10 → P16 (self-bootstrap)
              ├──→ P05 → P08 ──→ P16
              ├──→ P06 ────────→ P16
              └──→ P09 ────────→ P16
P04-P10 → P11 → P12 → P16
P04-P10 → P11 → P13 → P16
P04-P10 → P14 → P15 → P16
```

**Shortest path to self-bootstrap**: P01 → P03 → P05 → P06 → P08 → P11 → P12 → P16

---

## Full Test List

Tests are organized by level and module. Each test name encodes what it verifies. Tests marked with `[EDGE]` cover edge cases. Tests marked with `[SELF]` are specifically for the self-bootstrapping workflow.

### Unit Tests

#### Project Manager (`tests/unit/test_project_manager.py`)
```
test_create_project_returns_project_with_status_created
test_create_project_generates_unique_id
test_create_project_creates_directory_structure
test_create_project_from_template_copies_files
test_create_project_with_duplicate_name_raises_error [EDGE]
test_create_project_with_invalid_name_raises_validation_error [EDGE]
test_create_project_with_empty_name_raises_validation_error [EDGE]
test_create_project_name_with_special_characters_sanitized [EDGE]
test_list_projects_returns_all_projects
test_list_projects_empty_returns_empty_list
test_get_project_by_id_returns_correct_project
test_get_project_by_nonexistent_id_raises_not_found [EDGE]
test_delete_project_removes_directory
test_delete_project_nonexistent_raises_not_found [EDGE]
test_delete_running_project_stops_first [EDGE]
test_clone_project_from_git_url
test_clone_project_invalid_url_raises_error [EDGE]
test_clone_project_auth_failure_raises_error [EDGE]
test_clone_project_sets_status_cloned
test_project_status_transitions_are_valid
test_project_status_invalid_transition_raises_error [EDGE]
```

#### Code Manager (`tests/unit/test_code_manager.py`)
```
test_read_file_returns_content
test_read_file_nonexistent_raises_not_found [EDGE]
test_read_file_binary_returns_base64 [EDGE]
test_read_file_outside_project_raises_security_error [EDGE]
test_read_file_symlink_outside_project_raises_security_error [EDGE]
test_write_file_creates_new_file
test_write_file_updates_existing_file
test_write_file_creates_parent_directories
test_write_file_outside_project_raises_security_error [EDGE]
test_write_file_empty_content_allowed
test_write_file_very_large_content_handled [EDGE]
test_search_files_returns_matching_lines
test_search_files_regex_pattern
test_search_files_no_match_returns_empty
test_search_files_binary_files_skipped [EDGE]
test_diff_returns_unified_diff
test_diff_new_file_shows_all_additions
test_diff_deleted_file_shows_all_removals
test_diff_no_changes_returns_empty
test_list_files_returns_tree
test_list_files_respects_gitignore
test_list_files_hidden_files_option [EDGE]
```

#### Git Manager (`tests/unit/test_git_manager.py`)
```
test_status_returns_changed_files
test_status_clean_repo
test_status_untracked_files_included
test_add_stages_specific_files
test_add_nonexistent_file_raises_error [EDGE]
test_commit_creates_commit_with_message
test_commit_empty_staging_raises_error [EDGE]
test_commit_message_empty_raises_error [EDGE]
test_push_sends_to_remote
test_push_no_remote_raises_error [EDGE]
test_push_auth_failure_raises_error [EDGE]
test_push_with_retries_on_network_error [EDGE]
test_branch_creates_new_branch
test_branch_switch_existing
test_branch_duplicate_name_raises_error [EDGE]
test_branch_name_with_slashes_allowed
test_pr_create_returns_pr_url
test_pr_create_with_body
test_pr_merge_succeeds
test_pr_merge_with_conflicts_raises_error [EDGE]
test_pr_review_returns_comments
test_pr_review_no_comments_returns_empty
test_log_returns_commits
test_log_with_limit
test_log_empty_repo_returns_empty [EDGE]
test_diff_between_branches
test_actions_status_returns_workflow_runs
test_actions_logs_returns_output
test_actions_status_no_workflows_returns_empty [EDGE]
```

#### Runtime Manager (`tests/unit/test_runtime_manager.py`)
```
test_start_launches_nat_serve_process
test_start_with_config_path
test_start_already_running_raises_error [EDGE]
test_start_invalid_config_raises_error [EDGE]
test_start_port_in_use_raises_error [EDGE]
test_stop_terminates_process
test_stop_not_running_raises_error [EDGE]
test_stop_graceful_then_force [EDGE]
test_restart_stops_and_starts
test_status_returns_running_info
test_status_not_running_returns_stopped
test_logs_returns_recent_output
test_logs_with_line_limit
test_logs_streaming_yields_lines
test_health_check_returns_healthy
test_health_check_unhealthy_after_crash [EDGE]
test_start_captures_stderr [EDGE]
test_start_with_env_vars
```

#### Test Runner (`tests/unit/test_test_runner.py`)
```
test_run_unit_tests_returns_results
test_run_integration_tests_returns_results
test_run_e2e_tests_returns_results
test_run_specific_test_file
test_run_specific_test_function
test_results_include_pass_fail_skip_counts
test_results_include_failure_details
test_results_include_duration
test_results_include_coverage_percentage
test_run_no_tests_found_returns_empty_results [EDGE]
test_run_syntax_error_in_test_reports_error [EDGE]
test_run_timeout_kills_process [EDGE]
test_run_with_markers_filter
test_parse_pytest_json_output
test_parse_pytest_xml_output
test_coverage_below_threshold_flagged
```

#### Debug Manager (`tests/unit/test_debug_manager.py`)
```
test_get_errors_returns_recent_errors
test_get_errors_no_errors_returns_empty
test_get_errors_filters_by_severity
test_get_logs_returns_filtered_logs
test_get_logs_with_level_filter
test_get_logs_with_time_range
test_get_logs_with_pattern_match
test_get_stack_trace_from_error
test_get_stack_trace_multiline_parsed [EDGE]
test_profiler_data_returns_metrics
test_profiler_data_no_session_raises_error [EDGE]
```

#### Deploy Manager (`tests/unit/test_deploy_manager.py`)
```
test_build_docker_image_succeeds
test_build_no_dockerfile_raises_error [EDGE]
test_build_invalid_dockerfile_raises_error [EDGE]
test_push_image_to_registry
test_push_auth_failure_raises_error [EDGE]
test_deploy_local_docker_run
test_deploy_health_check_passes
test_deploy_health_check_fails_rolls_back [EDGE]
test_deploy_stop_previous_version
test_deploy_status_returns_info
test_deploy_no_image_raises_error [EDGE]
test_rollback_to_previous_version
test_rollback_no_previous_version_raises_error [EDGE]
```

#### Tool Orchestrator (`tests/unit/test_tool_orchestrator.py`)
```
test_execute_single_step_workflow
test_execute_multi_step_workflow
test_execute_step_failure_stops_workflow
test_execute_step_failure_with_retry
test_execute_parallel_steps
test_emit_event_on_step_completion
test_emit_event_on_workflow_failure
test_workflow_timeout [EDGE]
test_workflow_cancellation [EDGE]
test_workflow_with_conditional_steps
test_event_subscribers_notified
test_event_history_persisted
```

#### MCP Server (`tests/unit/test_mcp_server.py`)
```
test_server_registers_all_tools
test_server_tool_list_matches_spec
test_server_handles_tool_call_request
test_server_returns_tool_result
test_server_handles_unknown_tool_error [EDGE]
test_server_handles_malformed_request [EDGE]
test_server_registers_resources
test_server_handles_resource_read
test_server_resource_not_found_error [EDGE]
test_server_streamable_http_transport
test_server_jsonrpc_protocol_compliance
test_server_capabilities_negotiation
test_server_concurrent_requests [EDGE]
test_server_large_payload [EDGE]
test_server_well_known_endpoint
```

#### MCP Client (`tests/unit/test_mcp_client.py`)
```
test_client_connects_to_server
test_client_lists_available_tools
test_client_calls_tool
test_client_receives_tool_result
test_client_handles_connection_failure [EDGE]
test_client_handles_timeout [EDGE]
test_client_reconnects_after_disconnect [EDGE]
test_client_discovers_server_via_well_known
test_client_multiple_server_connections
test_client_reads_resource
test_client_resource_not_found_error [EDGE]
test_client_invalid_server_url_raises_error [EDGE]
```

#### OpenAPI Routes (`tests/unit/test_api_routes.py`)
```
test_health_endpoint_returns_200
test_list_projects_endpoint
test_create_project_endpoint
test_create_project_invalid_body_returns_422 [EDGE]
test_get_project_endpoint
test_get_project_not_found_returns_404 [EDGE]
test_delete_project_endpoint
test_read_file_endpoint
test_write_file_endpoint
test_git_status_endpoint
test_git_commit_endpoint
test_runtime_start_endpoint
test_runtime_stop_endpoint
test_runtime_logs_endpoint
test_test_run_endpoint
test_deploy_build_endpoint
test_openapi_spec_endpoint_returns_valid_spec
test_all_endpoints_have_openapi_docs
test_error_responses_follow_rfc7807 [EDGE]
test_cors_headers_present
test_request_id_header_propagated
```

#### Data Models (`tests/unit/test_models.py`)
```
test_project_model_serialization
test_project_model_deserialization
test_project_model_validation_rejects_invalid [EDGE]
test_event_model_serialization
test_event_model_deserialization
test_event_type_enum_complete
test_project_status_enum_complete
test_project_status_transition_validation
```

### Property-Based Tests (`tests/property/`)

```
# test_models_property.py
test_project_roundtrip_serialization — any valid Project serializes and deserializes identically
test_event_roundtrip_serialization — any valid ATTEvent serializes and deserializes identically
test_project_id_always_unique — generated IDs never collide (large sample)
test_project_name_sanitization_idempotent — sanitize(sanitize(x)) == sanitize(x)

# test_code_manager_property.py
test_write_then_read_roundtrip — write(content) then read() returns content for any content
test_search_finds_written_content — write(content) then search(substring_of_content) finds it
test_path_traversal_never_escapes_project — for any path, code_manager rejects paths outside project

# test_git_manager_property.py
test_commit_message_preserved — any commit message is retrievable from log
test_branch_name_sanitization — any valid branch name roundtrips through create/list

# test_mcp_server_property.py
test_tool_call_response_always_valid_jsonrpc — any tool call returns valid JSON-RPC response
test_resource_uri_always_parseable — any registered resource has a parseable URI
```

### Integration Tests (`tests/integration/`)

```
# test_project_lifecycle.py
test_create_project_then_list_includes_it
test_create_clone_start_stop_delete_lifecycle
test_create_project_then_read_default_files

# test_code_git_integration.py
test_write_file_then_git_status_shows_change
test_write_commit_push_workflow
test_diff_after_code_change

# test_runtime_integration.py
test_start_nat_serve_and_health_check
test_start_stop_start_lifecycle
test_logs_contain_startup_messages

# test_test_runner_integration.py
test_run_tests_on_sample_project
test_run_tests_reports_failure_correctly
test_coverage_report_generated

# test_mcp_integration.py
test_mcp_server_accepts_client_connection
test_mcp_client_calls_server_tool
test_mcp_roundtrip_tool_call_and_result

# test_api_integration.py
test_api_create_project_and_query
test_api_full_workflow_create_edit_test_commit
test_websocket_streaming_events
```

### End-to-End Tests (`tests/e2e/`)

```
# test_self_bootstrap.py [SELF]
test_att_registers_own_repo_as_project
test_att_reads_own_source_code [SELF]
test_att_runs_own_unit_tests [SELF]
test_att_creates_branch_on_own_repo [SELF]
test_att_edits_own_file_and_commits [SELF]
test_att_creates_pr_on_own_repo [SELF]
test_att_full_self_modification_cycle [SELF]
test_att_rollback_after_failed_self_test [SELF] [EDGE]
test_att_rejects_change_that_breaks_tests [SELF] [EDGE]
test_att_concurrent_self_modifications_serialize [SELF] [EDGE]

# test_web_ui.py (Playwright)
test_dashboard_loads_and_shows_projects
test_create_project_via_ui
test_open_project_shows_file_tree
test_edit_file_via_code_editor
test_run_tests_via_ui_and_see_results
test_view_git_status_and_diff
test_create_commit_via_ui
test_start_stop_runtime_via_ui
test_view_logs_streaming
test_deploy_via_ui
test_chat_view_sends_message_and_receives_response
test_settings_configure_mcp_server

# test_nat_app_creation.py
test_create_nat_app_from_template
test_configure_nat_app_via_ui
test_run_nat_app_and_interact
test_debug_nat_app_with_profiler
test_deploy_nat_app_locally

# test_mcp_e2e.py
test_external_mcp_client_connects_to_att
test_external_mcp_client_creates_project
test_external_mcp_client_full_workflow
test_att_as_mcp_client_uses_external_tool
test_mcp_tool_discovery_via_well_known
```

---

## Open Questions

> These must be resolved before implementation begins. We will iterate on this plan until all are answered.

### Architecture & Technology

1. **NAT-UI Integration Strategy**: Should we use the NAT-UI (Next.js) as-is via the git submodule, or fork it and extend with ATT-specific views (file tree, code editor, git, deploy)? The standard NAT-UI is a chat interface — ATT needs significantly more.

2. **Code Editor in Browser**: Which embeddable code editor should we use in the web UI? Options: Monaco Editor (VS Code engine), CodeMirror 6, or a simpler textarea with syntax highlighting. Monaco is heavy but feature-rich.

3. **NAT Version Pinning**: Which version of `nvidia-nat` should we target? The latest is 1.4.x but the API naming transitioned from `aiq.*` to `nat.*`. We need to confirm API stability.

4. **Python MCP SDK Version**: The official `mcp` Python SDK supports Streamable HTTP. Should we use it directly, or use NAT's built-in MCP integration (`nat.mcp`)?

5. **Database for Local Mode**: Is SQLite sufficient for local project metadata, or should we use something like TinyDB or even flat JSON files for maximum simplicity?

6. **Process Isolation**: How should ATT isolate managed NAT app processes? Options: subprocess, Docker container, or virtual environment only. Subprocess is simplest, Docker is safest.

### Self-Bootstrapping

7. **Safety Rails for Self-Modification**: What safeguards prevent ATT from breaking itself during self-modification? Proposed: mandatory passing tests + rollback on health check failure. Is this sufficient?

8. **CI Feedback Loop**: Should ATT poll GitHub Actions for CI results, or use webhooks? Polling is simpler; webhooks require a public endpoint or tunnel.

9. **Human Approval Gate**: Should the self-bootstrap cycle require human approval before merging, or can it be fully autonomous for green CI? This is a critical safety decision.

### Scope & Priority

10. **MCP Client Priority**: Which external MCP servers should be supported first? Claude Code is the obvious first choice for self-bootstrapping. Should we defer Windsurf/Codex to Phase 2?

11. **A2A Protocol**: NAT supports Agent-to-Agent protocol. Should ATT expose A2A endpoints in Phase 1 or defer to Phase 2?

12. **Offline Mode**: Should ATT work without internet access (no GitHub, no external MCP servers)? This affects whether git operations require a remote or can be purely local.

13. **NAT App Testing Mandate**: When ATT creates a NAT app, should it enforce TDD and refuse to deploy apps without passing tests? Or should it be advisory?

### Operations

14. **Docker Dependency**: The plan says "with or without Docker." For non-Docker local deployment, how does ATT manage NAT app processes? Direct subprocess with `nat serve`?

15. **Multi-Project Ports**: When running multiple NAT apps simultaneously, how should port allocation work? Auto-assign from a range? User-specified?

16. **Log Retention**: How long should ATT retain logs and test results? Options: configurable TTL, fixed (e.g., last 100 runs), or unlimited until manual cleanup.

---

## Priority Order for Implementation

The fastest path to self-bootstrapping:

```
Week 1:  P01 (skeleton) + P02 (CI) + P03 (models)
Week 2:  P05 (code mgr) + P06 (git mgr) — in parallel
Week 3:  P08 (test runner) + P11 (orchestrator)
Week 4:  P12 (MCP server) + P14 (OpenAPI routes)
Week 5:  P15 (web UI — minimal) + P13 (MCP client — Claude Code only)
Week 6:  P16 (self-bootstrap) + stabilization
```

After self-bootstrapping is achieved, ATT can assist in building its own remaining features (Phase 2 and Phase 3), dramatically accelerating development.

---

## Success Criteria

### Phase 0 Complete When:
- [ ] `uv run pytest tests/unit/` passes with > 80% coverage
- [ ] `ruff check` and `mypy --strict` pass with zero errors
- [ ] GitHub Actions Tier 1 runs in < 2 minutes
- [ ] All 8 core managers have passing interface tests

### Phase 1 (Self-Bootstrap) Complete When:
- [ ] ATT can read/write its own source files via the web UI
- [ ] ATT can run its own test suite and display results in the UI
- [ ] ATT can create a branch, make a change, commit, and push
- [ ] ATT can create a PR and verify CI passes
- [ ] ATT can merge a PR after CI passes
- [ ] ATT can rebuild and redeploy itself
- [ ] An external MCP client (e.g., Claude Code) can connect to ATT and perform all of the above
- [ ] All operations are available via both the REST API and MCP tools
- [ ] The full cycle works end-to-end: change → test → PR → CI → merge → deploy

### Phase 2 Complete When:
- [ ] A user can create a new NAT app from template, configure it, run it, test it, debug it, and deploy it — entirely through the web UI
- [ ] Created apps have TDD test suites with unit, integration, property, and e2e tests
- [ ] Created apps have their own CI pipelines

### Phase 3 Complete When:
- [ ] Multi-user with authentication works
- [ ] Cloud deployment (K8s) works
- [ ] OpenTelemetry traces and metrics are flowing
- [ ] Security audit passes with no critical findings
