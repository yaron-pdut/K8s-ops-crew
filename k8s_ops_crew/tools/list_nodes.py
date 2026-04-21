"""Tool: list_nodes — returns all nodes with readiness, capacity and allocatable resources."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from k8s_ops_crew.tools.k8s_client import get_core_v1

logger = logging.getLogger(__name__)


@tool
def list_nodes() -> list[dict[str, Any]]:
    """List all Kubernetes nodes with their readiness status and resource capacity.

    Returns:
        A list of dicts with keys: name, ready, roles, cpu_capacity,
        memory_capacity_gi, cpu_allocatable, memory_allocatable_gi,
        kernel_version, os_image, age_seconds.
    """
    core = get_core_v1()
    try:
        node_list = core.list_node()
    except Exception as exc:
        logger.error("list_nodes failed: %s", exc)
        raise

    results: list[dict[str, Any]] = []
    for node in node_list.items:
        meta = node.metadata or {}
        labels = meta.labels or {} if hasattr(meta, "labels") else {}

        # Determine roles from well-known label convention.
        roles = [
            key.split("/")[-1]
            for key in (labels if isinstance(labels, dict) else {})
            if key.startswith("node-role.kubernetes.io/")
        ]

        # Readiness condition.
        ready = "Unknown"
        if node.status and node.status.conditions:
            for cond in node.status.conditions:
                if cond.type == "Ready":
                    ready = cond.status  # "True" | "False" | "Unknown"
                    break

        # Capacity / allocatable.
        capacity = node.status.capacity if node.status else {}
        allocatable = node.status.allocatable if node.status else {}

        def _mem_gi(raw: str) -> float:
            """Convert Ki / Mi / Gi memory string to GiB float."""
            if not raw:
                return 0.0
            if raw.endswith("Ki"):
                return int(raw[:-2]) / (1024**2)
            if raw.endswith("Mi"):
                return int(raw[:-2]) / 1024
            if raw.endswith("Gi"):
                return float(raw[:-2])
            return float(raw) / (1024**3)

        age_seconds: float | None = None
        if node.metadata and node.metadata.creation_timestamp:
            import datetime

            age_seconds = (
                datetime.datetime.now(datetime.timezone.utc)
                - node.metadata.creation_timestamp
            ).total_seconds()

        node_info = node.status.node_info if node.status else None
        results.append(
            {
                "name": node.metadata.name if node.metadata else "",
                "ready": ready,
                "roles": roles or ["worker"],
                "cpu_capacity": capacity.get("cpu", "?") if isinstance(capacity, dict) else "?",
                "memory_capacity_gi": round(
                    _mem_gi(capacity.get("memory", "0") if isinstance(capacity, dict) else "0"), 2
                ),
                "cpu_allocatable": (
                    allocatable.get("cpu", "?") if isinstance(allocatable, dict) else "?"
                ),
                "memory_allocatable_gi": round(
                    _mem_gi(
                        allocatable.get("memory", "0") if isinstance(allocatable, dict) else "0"
                    ),
                    2,
                ),
                "kernel_version": node_info.kernel_version if node_info else None,
                "os_image": node_info.os_image if node_info else None,
                "age_seconds": age_seconds,
            }
        )

    logger.info("list_nodes returned %d nodes", len(results))
    return results
