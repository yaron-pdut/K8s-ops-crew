"""Shared LangGraph state definition for K8sOps Crew."""

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ClusterOpsState(TypedDict):
    """Typed shared state passed between all agents in the graph.

    Fields are accumulated across nodes; lists use ``add_messages``-style
    reducers where appending semantics are needed.
    """

    # User's natural-language intent for this run.
    user_intent: str

    # LangGraph message history (used by agent nodes for tool-call cycles).
    messages: Annotated[list, add_messages]

    # Supervisor's decomposed execution plan (list of phase names).
    plan: list[str]

    # Raw cluster data collected by the Diagnostics agent.
    cluster_snapshot: dict[str, Any]

    # Root-cause analysis produced by the Analyzer agent (Phase 2+).
    analysis: dict[str, Any]

    # Remediation proposals from the Remediator agent (Phase 3+).
    actions_proposed: list[dict[str, Any]]

    # Human-approved subset of proposed actions (Phase 3+).
    actions_approved: list[dict[str, Any]]

    # Final Markdown report produced by the Reporter agent.
    report: str

    # Which phase the supervisor is currently executing.
    current_phase: str

    # Accumulated error messages from any agent or tool.
    errors: list[str]
