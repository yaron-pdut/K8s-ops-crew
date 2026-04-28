"""Unit tests for the DiagnosticsAgent node."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from tests.conftest import FAKE_SNAPSHOT


def _make_llm_response(content: str, tool_calls: list | None = None) -> MagicMock:
    """Build a fake LLM AIMessage."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


class TestDiagnosticsNode:
    def test_snapshot_populated_from_llm_json(self) -> None:
        """DiagnosticsAgent parses JSON snapshot returned by LLM and stores it in state."""
        from k8s_ops_crew.agents.diagnostics import diagnostics_node

        llm_response = _make_llm_response(json.dumps(FAKE_SNAPSHOT))
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = llm_response

        with patch("k8s_ops_crew.agents.diagnostics._build_llm", return_value=mock_llm):
            result = diagnostics_node(
                {
                    "user_intent": "health summary",
                    "messages": [],
                    "errors": [],
                    "current_phase": "",
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                }
            )

        snapshot = result["cluster_snapshot"]
        assert len(snapshot["pods"]) == 2
        assert len(snapshot["nodes"]) == 1
        assert len(snapshot["events"]) == 1
        assert result["current_phase"] == "diagnosed"

    def test_tool_call_cycle_executed(self) -> None:
        """DiagnosticsAgent executes tool calls when LLM requests them."""
        from k8s_ops_crew.agents.diagnostics import diagnostics_node

        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {"name": "list_pods", "args": {}, "id": "call_1"},
        ]

        final_response = _make_llm_response(json.dumps(FAKE_SNAPSHOT))

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_call_response, final_response]

        fake_tool = MagicMock()
        fake_tool.name = "list_pods"
        fake_tool.invoke.return_value = FAKE_SNAPSHOT["pods"]

        with (
            patch("k8s_ops_crew.agents.diagnostics._build_llm", return_value=mock_llm),
            patch("k8s_ops_crew.agents.diagnostics._TOOLS", [fake_tool]),
        ):
            result = diagnostics_node(
                {
                    "user_intent": "health summary",
                    "messages": [],
                    "errors": [],
                    "current_phase": "",
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                }
            )

        fake_tool.invoke.assert_called_once_with({})
        assert result["current_phase"] == "diagnosed"

    def test_tool_error_appended_to_errors(self) -> None:
        """Tool failures are captured in state['errors'] without crashing."""
        from k8s_ops_crew.agents.diagnostics import diagnostics_node

        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {"name": "list_pods", "args": {}, "id": "call_err"},
        ]
        final_response = _make_llm_response(json.dumps(FAKE_SNAPSHOT))

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_call_response, final_response]

        broken_tool = MagicMock()
        broken_tool.name = "list_pods"
        broken_tool.invoke.side_effect = RuntimeError("connection refused")

        with (
            patch("k8s_ops_crew.agents.diagnostics._build_llm", return_value=mock_llm),
            patch("k8s_ops_crew.agents.diagnostics._TOOLS", [broken_tool]),
        ):
            result = diagnostics_node(
                {
                    "user_intent": "health summary",
                    "messages": [],
                    "errors": [],
                    "current_phase": "",
                    "plan": [],
                    "cluster_snapshot": {},
                    "analysis": {},
                    "actions_proposed": [],
                    "actions_approved": [],
                    "report": "",
                }
            )

        assert any("connection refused" in e for e in result["errors"])
