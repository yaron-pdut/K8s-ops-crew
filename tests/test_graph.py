"""End-to-end graph tests with mocked LLM and Kubernetes client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from tests.conftest import FAKE_SNAPSHOT


def _ai_message(content: str, tool_calls: list | None = None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


SUPERVISOR_PLAN = json.dumps(
    {
        "plan": ["assess", "diagnose", "report"],
        "current_phase": "diagnose",
        "summary": "Produce a cluster health summary.",
    }
)


class TestGraph:
    def _build_mock_llm(self) -> MagicMock:
        """Return a mock LLM that handles both supervisor and diagnostics calls."""
        llm = MagicMock()
        llm.bind_tools.return_value = llm

        # First call → supervisor planning (returns plan JSON).
        # Second call → supervisor after diagnostics (returns empty to trigger advance).
        # Third call → diagnostics (returns snapshot JSON).
        llm.invoke.side_effect = [
            _ai_message(SUPERVISOR_PLAN),           # supervisor first pass
            _ai_message(json.dumps(FAKE_SNAPSHOT)), # diagnostics
            _ai_message(""),                        # supervisor second pass (advance phase)
        ]
        return llm

    def test_graph_produces_report(self) -> None:
        """Full graph run with mocked LLM yields a non-empty report."""
        from k8s_ops_crew.graph import build_graph

        mock_llm = self._build_mock_llm()

        with patch("k8s_ops_crew.agents.supervisor.ChatOpenAI", return_value=mock_llm), \
             patch("k8s_ops_crew.agents.diagnostics.ChatOpenAI", return_value=mock_llm):

            graph = build_graph()
            result = graph.invoke(
                {
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
                },
                config={"configurable": {"thread_id": "test-run-1"}},
            )

        assert result["report"] != "", "Report must not be empty"
        assert "K8sOps Crew" in result["report"]

    def test_graph_report_contains_node_info(self) -> None:
        """Report includes node names from the cluster snapshot."""
        from k8s_ops_crew.graph import build_graph

        mock_llm = self._build_mock_llm()

        with patch("k8s_ops_crew.agents.supervisor.ChatOpenAI", return_value=mock_llm), \
             patch("k8s_ops_crew.agents.diagnostics.ChatOpenAI", return_value=mock_llm):

            graph = build_graph()
            result = graph.invoke(
                {
                    "user_intent": "health check",
                    "messages": [],
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                    "current_phase": "",
                    "errors": [],
                },
                config={"configurable": {"thread_id": "test-run-2"}},
            )

        assert "worker-1" in result["report"]

    def test_graph_captures_unhealthy_pod(self) -> None:
        """Report surfaces the CrashLoopBackOff pod from the snapshot."""
        from k8s_ops_crew.graph import build_graph

        mock_llm = self._build_mock_llm()

        with patch("k8s_ops_crew.agents.supervisor.ChatOpenAI", return_value=mock_llm), \
             patch("k8s_ops_crew.agents.diagnostics.ChatOpenAI", return_value=mock_llm):

            graph = build_graph()
            result = graph.invoke(
                {
                    "user_intent": "health check",
                    "messages": [],
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                    "current_phase": "",
                    "errors": [],
                },
                config={"configurable": {"thread_id": "test-run-3"}},
            )

        assert "broken-pod-xyz" in result["report"]

    def test_graph_final_phase_is_done(self) -> None:
        """Graph ends with current_phase == 'done'."""
        from k8s_ops_crew.graph import build_graph

        mock_llm = self._build_mock_llm()

        with patch("k8s_ops_crew.agents.supervisor.ChatOpenAI", return_value=mock_llm), \
             patch("k8s_ops_crew.agents.diagnostics.ChatOpenAI", return_value=mock_llm):

            graph = build_graph()
            result = graph.invoke(
                {
                    "user_intent": "health check",
                    "messages": [],
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                    "current_phase": "",
                    "errors": [],
                },
                config={"configurable": {"thread_id": "test-run-4"}},
            )

        assert result["current_phase"] == "done"
