# Phase 1: Foundation — K8sOps Crew

**Version**: 1.0  
**Author**: Yaron Pdut  
**Date**: April 2026  
**Status**: 🟡 In Progress

---

## Objective

Stand up the foundational skeleton of the K8sOps Crew multi-agent system:
a LangGraph-based supervisor + single Diagnostics agent that can connect to a Kubernetes cluster and produce a "cluster health summary".

---

## Deliverables

| # | Deliverable | Description |
 | --- | ------------- | ------------- |
| 1 | Project scaffold | Python package layout, pyproject.toml, linting/formatting config |
| 2 | LangGraph graph | Supervisor node + DiagnosticsAgent node with typed shared state |
| 3 | Kubernetes tools | Read-only tools: list pods, list nodes, get events, top nodes |
| 4 | Health summary endpoint | CLI entry-point + Gradio stub that accepts a natural-language intent |
| 5 | Test cluster config | kind cluster definition + RBAC ServiceAccount for the crew |
| 6 | Observability stub | LangSmith tracing wired in (LANGCHAIN_TRACING_V2=true) |
| 7 | Unit tests | pytest suite covering tools and graph nodes |

---

## Project File Structure

```text
K8s-ops-crew/
├── pyproject.toml                  # build metadata, deps, ruff/black config
├── Makefile                        # dev shortcuts: lint, test, run, kind-up
├── .env.example                    # env var template
├── k8s_ops_crew/                   # main Python package
│   ├── __init__.py
│   ├── main.py                     # CLI entry-point
│   ├── config.py                   # settings (pydantic-settings)
│   ├── state.py                    # LangGraph shared TypedDict state
│   ├── graph.py                    # LangGraph graph assembly
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── supervisor.py           # Orchestrator / Supervisor node
│   │   └── diagnostics.py         # Diagnostics / Health Agent node
│   └── tools/
│       ├── __init__.py
│       ├── k8s_client.py           # kubernetes Python client wrapper
│       ├── list_pods.py
│       ├── list_nodes.py
│       ├── get_events.py
│       └── top_nodes.py
├── infra/
│   ├── kind-cluster.yaml           # kind cluster definition
│   └── rbac/
│       ├── serviceaccount.yaml
│       ├── clusterrole.yaml        # read-only verbs only
│       └── clusterrolebinding.yaml
├── tests/
│   ├── conftest.py                 # fixtures: fake k8s client, mock LLM
│   ├── test_tools.py
│   ├── test_diagnostics_agent.py
│   └── test_graph.py
└── plans/
    └── phase1.md                   # this file
```

---

## Architecture

```mermaid
flowchart TD
    UI[User Intent - CLI or Gradio] --> SUP

    subgraph LangGraph State Graph
        SUP[Supervisor Agent\nDecomposes intent\nRoutes to agents]
        DIAG[Diagnostics Agent\nCollects cluster state]
        SUP -->|assess| DIAG
        DIAG -->|snapshot ready| SUP
        SUP -->|all done| RPT[Reporter stub\nFormats health summary]
    end

    subgraph Kubernetes Tools - read-only
        T1[list_pods]
        T2[list_nodes]
        T3[get_events]
        T4[top_nodes]
    end

    DIAG --> T1
    DIAG --> T2
    DIAG --> T3
    DIAG --> T4

    subgraph Observability
        LS[LangSmith Tracing]
    end

    LangGraph State Graph --> LS

    subgraph Test Cluster
        KIND[kind cluster]
        SA[ServiceAccount - read-only RBAC]
    end

    Kubernetes Tools - read-only --> KIND
```

---

## Task Breakdown

### Task 1 — Project Scaffold

- [ ] Initialise `pyproject.toml` with `[project]`, `[tool.ruff]`, `[tool.black]`, and `[tool.pytest.ini_options]` sections.
- [ ] Add dependencies: `langgraph`, `langchain`, `langchain-openai`, `kubernetes`, `pydantic-settings`, `pytest`, `ruff`, `black`.
- [ ] Create `Makefile` targets: `lint`, `format`, `test`, `kind-up`, `kind-down`, `run`.
- [ ] Create `.env.example` with `OPENAI_API_KEY`, `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2`, `KUBECONFIG`.
- [ ] Create `.gitignore` additions for `.env`, `__pycache__`, `.pytest_cache`.

### Task 2 — Shared State Definition

- [ ] Define [`ClusterOpsState`](k8s_ops_crew/state.py) as a `TypedDict` with fields:
  - `user_intent: str`
  - `plan: list[str]`
  - `cluster_snapshot: dict`
  - `analysis: dict`
  - `actions_proposed: list[dict]`
  - `actions_approved: list[dict]`
  - `report: str`
  - `current_phase: str`
  - `errors: list[str]`

### Task 3 — Kubernetes Read-Only Tools

- [ ] Implement [`k8s_client.py`](k8s_ops_crew/tools/k8s_client.py): load kubeconfig, expose typed CoreV1Api + AppsV1Api singletons.
- [ ] Implement [`list_pods()`](k8s_ops_crew/tools/list_pods.py): returns all pods across namespaces with status, restarts, age.
- [ ] Implement [`list_nodes()`](k8s_ops_crew/tools/list_nodes.py): returns nodes with Ready condition, capacity, allocatable.
- [ ] Implement [`get_events()`](k8s_ops_crew/tools/get_events.py): returns Warning events sorted by last timestamp.
- [ ] Implement [`top_nodes()`](k8s_ops_crew/tools/top_nodes.py): calls `metrics.k8s.io` API for CPU/memory usage.
- [ ] Wrap all tools as `@tool` (LangChain) decorated functions for agent binding.

### Task 4 — Diagnostics Agent

- [ ] Implement [`diagnostics.py`](k8s_ops_crew/agents/diagnostics.py) as a LangGraph node function.
- [ ] Bind the four K8s tools to the agent's LLM via `bind_tools(...)`.
- [ ] Agent fills `state["cluster_snapshot"]` with structured output.
- [ ] Handle tool errors gracefully; append to `state["errors"]`.

### Task 5 — Supervisor Agent

- [ ] Implement [`supervisor.py`](k8s_ops_crew/agents/supervisor.py) as a LangGraph node.
- [ ] Supervisor receives `user_intent`, produces a phased plan, sets `current_phase`.
- [ ] Routing logic: `assess → diagnostics → report` for Phase 1.
- [ ] Use `END` node when report is ready.

### Task 6 — Graph Assembly

- [ ] Implement [`graph.py`](k8s_ops_crew/graph.py): `StateGraph(ClusterOpsState)`, add nodes, add conditional edges.
- [ ] Compile graph with `MemorySaver` checkpointer for persistence.
- [ ] Wire LangSmith tracing via environment variables.

### Task 7 — CLI Entry-Point

- [ ] Implement [`main.py`](k8s_ops_crew/main.py): `python -m k8s_ops_crew "Give me a health summary"`.
- [ ] Stream graph events and pretty-print each agent step.
- [ ] Print final `state["report"]` to stdout.

### Task 8 — Test Cluster (kind)

- [ ] Write [`kind-cluster.yaml`](infra/kind-cluster.yaml) with 1 control-plane + 2 worker nodes.
- [ ] Write RBAC manifests: ServiceAccount `k8s-ops-crew`, ClusterRole with `get/list/watch` on pods, nodes, events, metrics.
- [ ] Add `Makefile` target `make kind-up` to create cluster and apply RBAC.

### Task 9 — Unit Tests

- [ ] `conftest.py`: fixture that patches `kubernetes.client` with a fake returning deterministic data.
- [ ] `test_tools.py`: each tool returns expected shape, handles API errors.
- [ ] `test_diagnostics_agent.py`: mock LLM, verify `cluster_snapshot` is populated.
- [ ] `test_graph.py`: end-to-end graph run with mocked LLM and K8s client returns a non-empty report.

---

## Dependencies

```toml
[project]
dependencies = [
  "langgraph>=0.2",
  "langchain>=0.3",
  "langchain-openai>=0.2",
  "kubernetes>=29.0",
  "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "ruff>=0.4",
  "black>=24.0",
]
```

---

## Definition of Done

- [ ] `make lint` passes with zero errors.
- [ ] `make test` passes all unit tests (≥ 80% coverage on `tools/` and `agents/`).
- [ ] `make run` with a live `kind` cluster produces a health summary report in stdout.
- [ ] LangSmith trace shows all agent steps visible.
- [ ] No write operations attempted — verified by RBAC (read-only ClusterRole).

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
 | ------ | ----------- | ------------ |
| `metrics.k8s.io` not available in kind by default | High | Enable `metrics-server` addon in kind config; fall back gracefully if unavailable |
| LLM structured output inconsistency | Medium | Use `with_structured_output(ClusterSnapshot)` schema enforcement |
| Kubeconfig path varies across environments | Low | Use `pydantic-settings` to allow `KUBECONFIG` env override |
| LangGraph API changes (fast-moving library) | Medium | Pin minor version in `pyproject.toml`; add renovate/dependabot |

---

## Next Phase Preview

**Phase 2** will add:

- Parallel diagnostics execution
- `AnalyzerAgent` with reflection loop ("critique this root cause")
- Full shared state transitions
- Basic HTML/Markdown report generation
