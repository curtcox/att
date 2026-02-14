# Dependency Analysis Across `todo/`

## Scope Reviewed
All markdown files under `todo/` were reviewed:
- `todo/master_plan.md`
- `todo/NEXT_MACHINE_HANDOFF.md`
- `todo/proposed_process_changes.md`
- `todo/plans/P01..P25` sub-plan files

This document identifies:
1. Declared dependencies
2. Dependency strength (how hard the coupling is in practice)
3. Work that can proceed independently

## Strength Rubric
- **Hard**: cannot deliver meaningful completion without the dependency.
- **Medium**: dependency can be stubbed or partial progress can proceed, but integration/completion needs it.
- **Soft**: mostly sequencing/preference; substantial work can proceed independently.

## Canonical Declared Graph (from `master_plan.md`)
- P01 → P02, P03
- P03 → P04, P05, P06, P07, P08, P09, P10
- P04/P05/P06/P08/P10 → P11, P12, P14
- P11 → P13
- P04..P13 → P16
- P14 → P15, P22, P24
- P04 → P17
- P15 → P18, P20, P21
- P12/P13 → P19
- P10/P22 → P23
- P14/P22 → P25

## Dependency Strength Assessment

### Foundation (P01-P03)
- **P01 → P02**: **Medium**
  - CI workflows can be drafted without full skeleton, but practical CI value depends on project layout and commands.
- **P01 → P03**: **Medium**
  - Data model schemas can be designed independently; implementation path and test wiring depend on project scaffolding.

### Core Managers (P04-P11)
- **P03 → P04/P05/P06**: **Hard**
  - Project/code/git managers rely on canonical project/event/store models.
- **P03 + P04 → P07**: **Hard**
  - Runtime manager depends on project identity/config and persisted state.
- **P03 + P05 → P08**: **Medium**
  - Test runner can run subprocess tests without code manager internals, but full API/tool integration assumes project/file abstractions.
- **P03 + P07 → P09**: **Hard**
  - Debug manager’s useful output is runtime-linked (logs/errors/profiler contexts).
- **P03 + P07 → P10**: **Hard**
  - Deploy manager and rollback semantics depend on runtime lifecycle + persisted metadata.
- **P04-P08 + P10 → P11**: **Medium/Hard mixed**
  - Hard for full orchestrated workflow value.
  - Medium for partial orchestrator framework/event bus skeleton.

### MCP/API/Self-bootstrap (P12-P16)
- **P04-P08 + P10 → P12**: **Medium/Hard mixed**
  - MCP surface can be scaffolded early (medium), but complete manager-backed tools/resources are hard-coupled.
- **P11 → P13**: **Medium**
  - `P13` is mostly transport/failover/client-state logic and has advanced independently in practice.
  - Orchestrator integration is beneficial but not always blocking for client core.
- **P04-P08 + P10 → P14**: **Medium**
  - Route contracts can be built with placeholders, but production-complete endpoint behavior needs manager completeness.
- **P14 → P15**: **Hard**
  - UI needs stable route contracts and behavior.
- **P04..P13 → P16**: **Medium/Hard mixed**
  - Hard for full autonomous loop (branch/edit/test/PR/deploy/rollback).
  - Medium for internal self-bootstrap manager control-plane scaffolding (already in progress).

### Phase 2/3 (P17-P25)
- **P04 → P17**: **Medium**
  - Template definitions/scaffolding can start independently; project lifecycle integration needed to finish.
- **P15 → P18/P20/P21**: **Hard**
  - These are UI-heavy capabilities requiring `P15` surface.
- **P12 + P13 → P19**: **Hard**
  - Registry/marketplace requires both server-side publication and client-side discovery/invocation.
- **P14 → P22/P24**: **Medium**
  - Auth/observability architecture can proceed, but broad adoption requires route layer integration.
- **P10 + P22 → P23**: **Hard**
  - Cloud deploy requires deployment primitives plus tenancy/auth controls.
- **P14 + P22 → P25**: **Hard**
  - Security hardening must be integrated with both API surface and identity/authorization model.

## What Can Be Done Independently (High-Leverage Parallel Work)

### Workstream A: MCP client hardening (mostly independent now)
Can proceed largely in parallel with unfinished manager details:
- Continue `P13` resilience/correlation/recovery matrix coverage.
- Extend adapter diagnostics, retry-window behavior, and convergence tests.
- Keep API diagnostics routes aligned (`/api/v1/mcp/*`) without waiting on UI.

Why independent: `P13` already has deep internal test scaffolding and only light coupling to orchestrator completeness.

### Workstream B: Runtime/Deploy/Debug triad
Parallelizable but coupled internally:
- `P07` runtime log/health gaps
- `P10` deploy and rollback policies
- `P09` debug extraction and profiler hooks

Why independent from many others: this stack can be validated mostly via unit/integration tests without waiting for web UI.

### Workstream C: API contract hardening before UI
- Drive `P14` to stable request/response/error contracts.
- Add consistency guarantees for RFC7807/error payloads and route-level typing.

Why independent: gives `P15` a stable base and avoids UI churn.

### Workstream D: CI/process hygiene
- Continue process-change trials (snapshot script, doc guardrails, archive policy).
- Keep docs bounded and machine-handoff automation consistent.

Why independent: low coupling to product feature delivery; improves delivery throughput.

## Strong Coupling Bottlenecks (Critical for Throughput)
1. **`P15` (web_ui)** is a gate for multiple future plans (`P18`, `P20`, `P21`).
2. **`P22` (multi_user)** gates `P23` and `P25`; delaying identity model delays cloud/security hardening.
3. **`P10` (deploy_manager)** quality directly affects `P16` self-bootstrap safety and `P23` cloud readiness.
4. **`P14` (openapi_routes)** maturity is the major contract boundary for UI and external integrations.

## Suggested Execution Order to Maximize Parallelism
1. Finish `P07`, `P10`, `P14` to stabilize runtime/deploy/API contracts.
2. Run `P13` hardening in parallel (ongoing) with minimal blocking dependencies.
3. Start `P15` once `P14` contracts are stable enough.
4. Split post-UI work into parallel tracks:
   - Track 1: `P18` + `P20`
   - Track 2: `P21`
5. Start `P22` as soon as route-level auth insertion points in `P14` are stable.
6. Then execute `P23` and `P25` in parallel where feasible (shared dependency `P22`).

## Confidence Notes
- **High confidence** in declared graph and Phase-level gates (explicit in `master_plan.md`).
- **Medium confidence** on edge strength where plan files are placeholders and do not yet specify concrete interfaces.
- **High confidence** that `P13` currently supports substantial independent progress due to detailed implemented notes and broad test surface.
