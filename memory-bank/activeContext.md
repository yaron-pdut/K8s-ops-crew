# Active Context — K8sOps Crew

**Last Updated**: April 2026  
**Current Phase**: Phase 1 — Foundation

---

## What We Are Building

**K8sOps Crew** is a multi-agent AI system that acts as an autonomous SRE assistant for Kubernetes clusters. It uses a **hierarchical supervisor pattern** built on **LangGraph** with read-only Kubernetes tooling in Phase 1.

---

## Current Focus

**Phase 1 — COMPLETE ✅**

### Task Status

| Task | Status |
| ------ | -------- |
| Project scaffold (`pyproject.toml`, `Makefile`, `.env.example`) | ✅ Done |
| Shared state definition (`ClusterOpsState` TypedDict) | ✅ Done |
| Kubernetes read-only tools (`list_pods`, `list_nodes`, `get_events`, `top_nodes`) | ✅ Done |
| Diagnostics Agent (LangGraph node) | ✅ Done |
| Supervisor Agent (LangGraph node) | ✅ Done |
| Graph assembly (`StateGraph`, `MemorySaver`) | ✅ Done |
| CLI entry-point (`main.py`) | ✅ Done |
| kind test cluster + RBAC manifests | ✅ Done |
| Unit tests (`pytest` suite) | ✅ Done — 23/23 passed, 80.70% coverage |

### Next Focus: Phase 2 — Core Workflow

- Add `AnalyzerAgent` with reflection/critique loop
- Parallel diagnostics execution via LangGraph fan-out
- Full `ReporterAgent` (Markdown/HTML output)
- Prometheus / OpenTelemetry metrics integration

---

## Key Architectural Decisions

- **Orchestration**: LangGraph `StateGraph` with typed shared state (`ClusterOpsState`).
- **LLM**: OpenAI GPT-4o-class (configurable via `pydantic-settings`).
- **K8s client**: `kubernetes` Python library; read-only RBAC scoped to `get/list/watch`.
- **Tools**: LangChain `@tool` decorated functions bound to agent LLMs.
- **Persistence**: `MemorySaver` checkpointer (in-process for Phase 1).
- **Observability**: LangSmith tracing via `LANGCHAIN_TRACING_V2=true`.
- **Test cluster**: `kind` with 1 control-plane + 2 workers; `metrics-server` addon enabled.

---

## Important Files

| File | Purpose |
 | ------ | --------- |
| [`README.md`](../README.md) | Full project overview and roadmap |
| [`plans/phase1.md`](../plans/phase1.md) | Detailed Phase 1 plan and task breakdown |
| [`memory-bank/progress.md`](progress.md) | Phase-by-phase progress tracker |

---

## Environment Variables Required

```shell
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=k8s-ops-crew
KUBECONFIG=~/.kube/config
```

---

## Definition of Done for Phase 1

- `make lint` passes with zero errors.
- `make test` passes all unit tests (≥ 80% coverage on `tools/` and `agents/`).
- `make run` with a live `kind` cluster produces a health summary in stdout.
- LangSmith trace shows all agent steps.
- No write operations attempted — verified by read-only RBAC.
