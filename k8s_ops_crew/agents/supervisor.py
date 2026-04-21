"""Supervisor Agent — decomposes user intent and routes between graph nodes."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from k8s_ops_crew.config import settings
from k8s_ops_crew.state import ClusterOpsState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Orchestrator of a Kubernetes SRE multi-agent system called K8sOps Crew.

Your responsibilities:
1. Receive the user's intent.
2. Decompose it into a clear, ordered execution plan.
3. Set the current phase so downstream agents know what to do.

For Phase 1 the only available pipeline is:
  assess → diagnose → report

Always return ONLY valid JSON (no markdown fences) with this exact schema:
{
  "plan": ["assess", "diagnose", "report"],
  "current_phase": "diagnose",
  "summary": "<one-sentence description of what you understood>"
}
"""


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.supervisor_model,
        temperature=0,
    )


def supervisor_node(state: ClusterOpsState) -> dict[str, Any]:
    """LangGraph node: produce an execution plan from the user intent.

    If called after diagnostics (current_phase == 'diagnosed'), the supervisor
    advances the phase to 'report'. Otherwise it initialises the plan and
    routes to 'diagnose'.
    """
    import json

    current_phase = state.get("current_phase", "")
    errors: list[str] = list(state.get("errors", []))

    # Second pass: diagnostics is done, advance to reporting.
    if current_phase == "diagnosed":
        logger.info("Supervisor: diagnostics complete, advancing to report phase")
        return {"current_phase": "report", "errors": errors}

    # First pass: plan the run.
    logger.info("Supervisor: planning run for intent: %s", state.get("user_intent"))

    llm = _build_llm()
    messages = list(state.get("messages", []))
    messages.append(
        HumanMessage(
            content=(
                f"{_SYSTEM_PROMPT}\n\n"
                f"User intent: {state.get('user_intent', 'Give me a health summary.')}"
            )
        )
    )

    response = llm.invoke(messages)
    messages.append(response)

    plan = ["assess", "diagnose", "report"]
    try:
        text = response.content
        if isinstance(text, list):
            text = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block) for block in text
            )
        parsed = json.loads(text)
        plan = parsed.get("plan", plan)
        logger.info("Supervisor plan: %s | summary: %s", plan, parsed.get("summary", ""))
    except (json.JSONDecodeError, TypeError) as exc:
        err = f"Supervisor: failed to parse plan JSON: {exc}"
        logger.warning(err)
        errors.append(err)

    return {
        "messages": messages,
        "plan": plan,
        "current_phase": "diagnose",
        "errors": errors,
    }
