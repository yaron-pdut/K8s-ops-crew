"""End-to-end graph tests — node functions are patched to avoid LLM/message-channel issues."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from tests.conftest import (
    FAKE_SNAPSHOT,
)

# ---------------------------------------------------------------------------
# Fake node implementations
# ---------------------------------------------------------------------------


def _fake_supervisor(state: dict[str, Any]) -> dict[str, Any]:
    """Stand-in for supervisor_node: sets plan and advances phase."""
    phase = state.get("current_phase", "")
    if phase == "diagnosed":
        return {"current_phase": "report", "errors": state.get("errors", [])}
    return {
        "messages": state.get("messages", []),
        "plan": ["assess", "diagnose", "report"],
        "current_phase": "diagnose",
        "errors": state.get("errors", []),
    }


def _fake_diagnostics(state: dict[str, Any]) -> dict[str, Any]:
    """Stand-in for diagnostics_node: injects FAKE_SNAPSHOT."""
    return {
        "messages": state.get("messages", []),
        "cluster_snapshot": FAKE_SNAPSHOT,
        "errors": state.get("errors", []),
        "current_phase": "diagnosed",
    }


_INITIAL_STATE: dict[str, Any] = {
    "user_intent": "Give me a health summary",
    "messages": [],
    "plan": [],
    "cluster_snapshot": {},
    "analysis": {},
    "actions_proposed": [],
    "actions_approved": [],
    "report": "",
    "current_phase": "",
    "errors": [],
}


class TestGraph:
    def _run_graph(self, thread_id: str) -> dict[str, Any]:
        from k8s_ops_crew.graph import build_graph

        with (
            patch("k8s_ops_crew.graph.supervisor_node", side_effect=_fake_supervisor),
            patch("k8s_ops_crew.graph.diagnostics_node", side_effect=_fake_diagnostics),
        ):
            graph = build_graph()
            return graph.invoke(
                dict(_INITIAL_STATE),
                config={"configurable": {"thread_id": thread_id}},
            )

    def test_graph_produces_report(self) -> None:
        """Full graph run yields a non-empty Markdown report."""
        result = self._run_graph("test-run-1")
        assert result["report"] != "", "Report must not be empty"
        assert "K8sOps Crew" in result["report"]

    def test_graph_report_contains_node_info(self) -> None:
        """Report includes node names from the cluster snapshot."""
        result = self._run_graph("test-run-2")
        assert "worker-1" in result["report"]

    def test_graph_captures_unhealthy_pod(self) -> None:
        """Report surfaces the CrashLoopBackOff pod from the snapshot."""
        result = self._run_graph("test-run-3")
        assert "broken-pod-xyz" in result["report"]

    def test_graph_final_phase_is_done(self) -> None:
        """Graph ends with current_phase == 'done'."""
        result = self._run_graph("test-run-4")
        assert result["current_phase"] == "done"

    def test_graph_warning_event_in_report(self) -> None:
        """Report includes the BackOff warning event."""
        result = self._run_graph("test-run-5")
        assert "BackOff" in result["report"]

    def test_graph_node_metrics_in_report(self) -> None:
        """Report includes node metrics section when metrics are present."""
        result = self._run_graph("test-run-6")
        assert "Node Resource Usage" in result["report"]

    def test_reporter_node_directly(self) -> None:
        """reporter_node produces a valid report from a pre-built snapshot."""
        from k8s_ops_crew.graph import reporter_node

        state: dict[str, Any] = {
            "user_intent": "test intent",
            "cluster_snapshot": FAKE_SNAPSHOT,
            "errors": [],
            "messages": [],
            "plan": [],
            "analysis": {},
            "actions_proposed": [],
            "actions_approved": [],
            "report": "",
            "current_phase": "report",
        }
        result = reporter_node(state)
        assert "K8sOps Crew" in result["report"]
        assert result["current_phase"] == "done"

    def test_reporter_node_with_errors(self) -> None:
        """reporter_node includes error section when errors are present."""
        from k8s_ops_crew.graph import reporter_node

        state: dict[str, Any] = {
            "user_intent": "test",
            "cluster_snapshot": {"pods": [], "nodes": [], "events": [], "node_metrics": []},
            "errors": ["tool X failed: connection refused"],
            "messages": [],
            "plan": [],
            "analysis": {},
            "actions_proposed": [],
            "actions_approved": [],
            "report": "",
            "current_phase": "report",
        }
        result = reporter_node(state)
        assert "Errors During Collection" in result["report"]
        assert "connection refused" in result["report"]
