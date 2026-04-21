"""Tool: list_pods — returns all pods across namespaces with status summary."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from k8s_ops_crew.tools.k8s_client import get_core_v1

logger = logging.getLogger(__name__)


@tool
def list_pods(namespace: str = "") -> list[dict[str, Any]]:
    """List all Kubernetes pods, optionally filtered by namespace.

    Args:
        namespace: If empty, lists pods across all namespaces.

    Returns:
        A list of dicts with keys: name, namespace, phase, ready,
        restarts, node, age_seconds.
    """
    core = get_core_v1()
    try:
        if namespace:
            pod_list = core.list_namespaced_pod(namespace=namespace)
        else:
            pod_list = core.list_pod_for_all_namespaces()
    except Exception as exc:
        logger.error("list_pods failed: %s", exc)
        raise

    results: list[dict[str, Any]] = []
    for pod in pod_list.items:
        restarts = 0
        ready_containers = 0
        total_containers = len(pod.spec.containers) if pod.spec else 0

        if pod.status and pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                restarts += cs.restart_count or 0
                if cs.ready:
                    ready_containers += 1

        age_seconds: float | None = None
        if pod.metadata and pod.metadata.creation_timestamp:
            import datetime

            age_seconds = (
                datetime.datetime.now(datetime.UTC)
                - pod.metadata.creation_timestamp
            ).total_seconds()

        results.append(
            {
                "name": pod.metadata.name if pod.metadata else "",
                "namespace": pod.metadata.namespace if pod.metadata else "",
                "phase": pod.status.phase if pod.status else "Unknown",
                "ready": f"{ready_containers}/{total_containers}",
                "restarts": restarts,
                "node": pod.spec.node_name if pod.spec else None,
                "age_seconds": age_seconds,
            }
        )

    logger.info("list_pods returned %d pods", len(results))
    return results
