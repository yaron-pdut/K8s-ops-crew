"""Tool: get_events — returns Warning-level cluster events sorted by recency."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from k8s_ops_crew.tools.k8s_client import get_core_v1

logger = logging.getLogger(__name__)


@tool
def get_events(namespace: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Fetch Kubernetes Warning events, sorted by most-recent first.

    Args:
        namespace: If empty, fetches events across all namespaces.
        limit: Maximum number of events to return (default 50).

    Returns:
        A list of dicts with keys: namespace, name, reason, message,
        involved_object_kind, involved_object_name, count,
        first_time, last_time, type.
    """
    core = get_core_v1()
    try:
        if namespace:
            event_list = core.list_namespaced_event(namespace=namespace)
        else:
            event_list = core.list_event_for_all_namespaces()
    except Exception as exc:
        logger.error("get_events failed: %s", exc)
        raise

    warning_events = [e for e in event_list.items if e.type == "Warning"]

    # Sort by last_timestamp descending (most recent first).
    warning_events.sort(
        key=lambda e: e.last_timestamp or e.event_time or "",
        reverse=True,
    )

    results: list[dict[str, Any]] = []
    for event in warning_events[:limit]:
        meta = event.metadata
        involved = event.involved_object
        results.append(
            {
                "namespace": meta.namespace if meta else "",
                "name": meta.name if meta else "",
                "reason": event.reason or "",
                "message": event.message or "",
                "involved_object_kind": involved.kind if involved else "",
                "involved_object_name": involved.name if involved else "",
                "count": event.count or 1,
                "first_time": str(event.first_timestamp) if event.first_timestamp else None,
                "last_time": str(event.last_timestamp) if event.last_timestamp else None,
                "type": event.type or "Warning",
            }
        )

    logger.info("get_events returned %d warning events", len(results))
    return results
