"""Diagnostics Agent — collects cluster state into shared ClusterOpsState."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from k8s_ops_crew.config import settings
from k8s_ops_crew.state import ClusterOpsState
from k8s_ops_crew.tools.get_events import get_events
from k8s_ops_crew.tools.list_nodes import list_nodes
from k8s_ops_crew.tools.list_pods import list_pods
from k8s_ops_crew.tools.top_nodes import top_nodes

logger = logging.getLogger(__name__)

_TOOLS = [list_pods, list_nodes, get_events, top_nodes]

_SYSTEM_PROMPT = """\
You are a Kubernetes Diagnostics Agent. Your job is to collect a comprehensive
snapshot of the current cluster state using the tools provided.

Call ALL four tools — list_pods, list_nodes, get_events, top_nodes — and
assemble the results. Do not skip any tool. If a tool raises an error, record
the error message and continue with the remaining tools.

Return ONLY a JSON object (no markdown fences) with keys:
  pods, nodes, events, node_metrics
where each value is the list returned by the corresponding tool (or an empty
list on error).
"""


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.diagnostics_model,
        temperature=0,
    ).bind_tools(_TOOLS)


def diagnostics_node(state: ClusterOpsState) -> dict[str, Any]:
    """LangGraph node: run all K8s read tools and populate cluster_snapshot."""
    logger.info("DiagnosticsAgent: starting cluster snapshot")

    llm = _build_llm()
    messages = list(state.get("messages", []))
    errors: list[str] = list(state.get("errors", []))

    # Seed the conversation with the diagnostic task.
    messages.append(
        HumanMessage(
            content=(
                f"{_SYSTEM_PROMPT}\n\n"
                f"User intent: {state.get('user_intent', 'health summary')}"
            )
        )
    )

    # Agentic tool-call loop (max 10 iterations to prevent runaway).
    snapshot: dict[str, Any] = {"pods": [], "nodes": [], "events": [], "node_metrics": []}

    for _iteration in range(10):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            # LLM returned final text — attempt to parse JSON.
            try:
                text = response.content
                if isinstance(text, list):
                    # Structured content blocks (e.g. Claude) — join text parts.
                    text = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in text
                    )
                snapshot = json.loads(text)
            except (json.JSONDecodeError, TypeError) as exc:
                err = f"DiagnosticsAgent: failed to parse JSON response: {exc}"
                logger.warning(err)
                errors.append(err)
            break

        # Execute each tool call.
        tool_map = {t.name: t for t in _TOOLS}
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_fn = tool_map.get(tool_name)
            if tool_fn is None:
                result = f"Unknown tool: {tool_name}"
            else:
                try:
                    result = tool_fn.invoke(tool_args)
                except Exception as exc:
                    result = f"ERROR: {exc}"
                    errors.append(f"{tool_name}: {exc}")
                    logger.error("Tool %s failed: %s", tool_name, exc)

            messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    tool_call_id=tc["id"],
                )
            )

    logger.info(
        "DiagnosticsAgent: snapshot collected — pods=%d, nodes=%d, events=%d, metrics=%d",
        len(snapshot.get("pods", [])),
        len(snapshot.get("nodes", [])),
        len(snapshot.get("events", [])),
        len(snapshot.get("node_metrics", [])),
    )

    return {
        "messages": messages,
        "cluster_snapshot": snapshot,
        "errors": errors,
        "current_phase": "diagnosed",
    }
