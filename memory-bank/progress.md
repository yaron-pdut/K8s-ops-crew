# Progress Tracker — K8sOps Crew

**Last Updated**: April 2026

---

## Phase Overview

| Phase | Title | Status |
 | ------- | ------- | -------- |
| Phase 1 | Foundation | 🟡 In Progress |
| Phase 2 | Core Workflow | 🔲 Not Started |
| Phase 3 | Optimization & Remediation | 🔲 Not Started |
| Phase 4 | Verification, Polish & Testing | 🔲 Not Started |
| Phase 5 | Extensions & Production Readiness | 🔲 Not Started |

---

## Phase 1: Foundation — Detailed Progress

**Goal**: Supervisor + DiagnosticsAgent + K8s read-only tools → cluster health summary.

### Scaffold & Config

- [ ] `pyproject.toml` with deps, ruff, black, pytest config
- [ ] `Makefile` with `lint`, `format`, `test`, `kind-up`, `kind-down`, `run`
- [ ] `.env.example` with all required env vars
- [ ] Package skeleton: `k8s_ops_crew/`, `tests/`, `infra/`

### Core Modules

- [ ] [`k8s_ops_crew/state.py`](../k8s_ops_crew/state.py) — `ClusterOpsState` TypedDict
- [ ] [`k8s_ops_crew/config.py`](../k8s_ops_crew/config.py) — pydantic-settings `Settings`
- [ ] [`k8s_ops_crew/tools/k8s_client.py`](../k8s_ops_crew/tools/k8s_client.py) — K8s client singleton
- [ ] [`k8s_ops_crew/tools/list_pods.py`](../k8s_ops_crew/tools/list_pods.py)
- [ ] [`k8s_ops_crew/tools/list_nodes.py`](../k8s_ops_crew/tools/list_nodes.py)
- [ ] [`k8s_ops_crew/tools/get_events.py`](../k8s_ops_crew/tools/get_events.py)
- [ ] [`k8s_ops_crew/tools/top_nodes.py`](../k8s_ops_crew/tools/top_nodes.py)
- [ ] [`k8s_ops_crew/agents/diagnostics.py`](../k8s_ops_crew/agents/diagnostics.py)
- [ ] [`k8s_ops_crew/agents/supervisor.py`](../k8s_ops_crew/agents/supervisor.py)
- [ ] [`k8s_ops_crew/graph.py`](../k8s_ops_crew/graph.py)
- [ ] [`k8s_ops_crew/main.py`](../k8s_ops_crew/main.py)

### Infrastructure

- [ ] [`infra/kind-cluster.yaml`](../infra/kind-cluster.yaml)
- [ ] [`infra/rbac/serviceaccount.yaml`](../infra/rbac/serviceaccount.yaml)
- [ ] [`infra/rbac/clusterrole.yaml`](../infra/rbac/clusterrole.yaml)
- [ ] [`infra/rbac/clusterrolebinding.yaml`](../infra/rbac/clusterrolebinding.yaml)

### Tests

- [ ] [`tests/conftest.py`](../tests/conftest.py)
- [ ] [`tests/test_tools.py`](../tests/test_tools.py)
- [ ] [`tests/test_diagnostics_agent.py`](../tests/test_diagnostics_agent.py)
- [ ] [`tests/test_graph.py`](../tests/test_graph.py)

### Definition of Done Checklist

- [ ] `make lint` — zero errors
- [ ] `make test` — all pass, ≥ 80% coverage on `tools/` and `agents/`
- [ ] `make run` — health summary printed to stdout against live kind cluster
- [ ] LangSmith trace visible with all agent steps
- [ ] No write operations — confirmed by read-only RBAC

---

## Phase 2: Core Workflow — Preview

**Goal**: Parallel diagnostics, `AnalyzerAgent` with reflection loop, basic report generation.

Agents to add:

- `AnalyzerAgent` — correlates metrics, logs, events; reflection/critique loop.
- `ReporterAgent` (full) — Markdown/HTML report.

State additions:

- `analysis: dict` with root causes, severity scores.
- `report_html: str`.

---

## Phase 3: Optimization & Remediation — Preview

**Goal**: `OptimizerAgent`, `RemediatorAgent` with dry-run + human approval gates.

Key safety work:

- Approval interrupt node in LangGraph.
- Dry-run flag propagated through all mutating tools.
- Prometheus metrics integration.

---

## Phase 4: Verification, Polish & Testing — Preview

**Goal**: `VerifierAgent`, failure injection tests, LangSmith metrics dashboard.

Metrics to track:

- Success rate per run.
- Mean agent turns to resolution.
- Token cost per run.
- Wall-clock time to resolution.

---

## Phase 5: Production Readiness — Preview

**Goal**: Deploy crew on Kubernetes, multi-cluster, predictive detection, security scanning.

Infrastructure:

- Crew packaged as Docker image; deployed as K8s `Deployment`.
- Workload identity (SPIFFE/SPIRE).
- NetworkPolicies, Pod Security Standards, image scanning.
- CronJob for scheduled scans.

---

## Decisions Log

| Date | Decision | Rationale |
 | ------ | ---------- | ----------- |
| April 2026 | Use LangGraph over CrewAI | Better controllability, stateful graphs, human-in-the-loop primitives |
| April 2026 | Read-only RBAC in Phase 1 | Safety first; no writes until approval gates are implemented in Phase 3 |
| April 2026 | kind for test cluster | Fast local iteration; metrics-server addon available |
| April 2026 | pydantic-settings for config | Type-safe env var handling, consistent with Python best practices |
| April 2026 | MemorySaver for Phase 1 persistence | In-process is sufficient for single-run CLI; upgrade to Redis/Postgres in Phase 5 |
