"""LangGraph graph assembly for K8sOps Crew — Phase 1.

Graph topology (Phase 1):
    supervisor → diagnostics → supervisor → reporter → END
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from k8s_ops_crew.agents.diagnostics import diagnostics_node
from k8s_ops_crew.agents.supervisor import supervisor_node
from k8s_ops_crew.state import ClusterOpsState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reporter node (Phase 1 stub — full implementation in Phase 2)
# ---------------------------------------------------------------------------


def reporter_node(state: ClusterOpsState) -> dict[str, Any]:
    """Compile cluster_snapshot into a Markdown health summary report."""
    snapshot = state.get("cluster_snapshot", {})
    pods: list = snapshot.get("pods", [])
    nodes: list = snapshot.get("nodes", [])
    events: list = snapshot.get("events", [])
    metrics: list = snapshot.get("node_metrics", [])
    errors: list = state.get("errors", [])

    not_running = [p for p in pods if p.get("phase") not in ("Running", "Succeeded")]
    warning_nodes = [n for n in nodes if n.get("ready") != "True"]

    lines: list[str] = [
        "# K8sOps Crew — Cluster Health Summary",
        "",
        f"**Intent**: {state.get('user_intent', '')}",
        "",
        "## Nodes",
        f"- Total: {len(nodes)}",
        f"- Not Ready: {len(warning_nodes)}",
    ]

    for node in nodes:
        lines.append(
            f"  - `{node['name']}` ready={node.get('ready')} "
            f"cpu={node.get('cpu_allocatable')} "
            f"mem={node.get('memory_allocatable_gi')}Gi"
        )

    if metrics:
        lines += ["", "## Node Resource Usage"]
        for m in metrics:
            if not isinstance(m, dict):
                continue
            lines.append(
                f"  - `{m.get('name', '?')}` "
                f"cpu={m.get('cpu_millicores', '?')}m "
                f"mem={m.get('memory_mi', '?')}Mi"
            )

    lines += [
        "",
        "## Pods",
        f"- Total: {len(pods)}",
        f"- Unhealthy (non-Running/Succeeded): {len(not_running)}",
    ]
    for pod in not_running[:20]:
        if not isinstance(pod, dict):
            continue
        lines.append(
            f"  - `{pod.get('namespace', '?')}/{pod.get('name', '?')}` "
            f"phase={pod.get('phase')} restarts={pod.get('restarts', 0)}"
        )

    lines += [
        "",
        "## Warning Events",
        f"- Total Warning events: {len(events)}",
    ]
    for evt in events[:10]:
        if not isinstance(evt, dict):
            continue
        lines.append(
            f"  - `{evt.get('involved_object_kind', '?')}/{evt.get('involved_object_name', '?')}` "
            f"reason={evt.get('reason', '?')} count={evt.get('count', '?')} "
            f"— {str(evt.get('message', ''))[:120]}"
        )

    if errors:
        lines += ["", "## Errors During Collection"]
        for err in errors:
            lines.append(f"  - ⚠️ {err}")

    report = "\n".join(lines)
    logger.info("ReporterNode: report generated (%d chars)", len(report))
    return {"report": report, "current_phase": "done"}


# ---------------------------------------------------------------------------
# Routing function
# ---------------------------------------------------------------------------


def _route_supervisor(state: ClusterOpsState) -> Literal["diagnostics", "reporter", "__end__"]:
    """Decide the next node based on the current phase set by the supervisor."""
    phase = state.get("current_phase", "")
    if phase == "diagnose":
        return "diagnostics"
    if phase == "report":
        return "reporter"
    return "__end__"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def build_graph(checkpointer: MemorySaver | None = None) -> Any:
    """Assemble and compile the Phase 1 LangGraph state graph.

    Args:
        checkpointer: Optional persistence backend. Defaults to MemorySaver.

    Returns:
        A compiled LangGraph runnable.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(ClusterOpsState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("diagnostics", diagnostics_node)
    graph.add_node("reporter", reporter_node)

    # Entry point.
    graph.add_edge(START, "supervisor")

    # Supervisor routes based on phase.
    graph.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {
            "diagnostics": "diagnostics",
            "reporter": "reporter",
            "__end__": END,
        },
    )

    # After diagnostics, return to supervisor to advance phase.
    graph.add_edge("diagnostics", "supervisor")

    # After reporter, we are done.
    graph.add_edge("reporter", END)

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Graph compiled successfully")
    return compiled
