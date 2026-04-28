"""Tool: top_nodes — fetches CPU and memory usage from the metrics.k8s.io API."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from k8s_ops_crew.tools.k8s_client import get_custom_objects

logger = logging.getLogger(__name__)

_METRICS_GROUP = "metrics.k8s.io"
_METRICS_VERSION = "v1beta1"
_METRICS_PLURAL = "nodes"


def _parse_cpu_millicores(raw: str) -> float:
    """Convert a CPU quantity string (e.g. '125m', '2') to millicores float."""
    if not raw:
        return 0.0
    if raw.endswith("n"):
        return float(raw[:-1]) / 1_000_000
    if raw.endswith("u"):
        return float(raw[:-1]) / 1_000
    if raw.endswith("m"):
        return float(raw[:-1])
    return float(raw) * 1000


def _parse_mem_mi(raw: str) -> float:
    """Convert a memory quantity string to MiB float."""
    if not raw:
        return 0.0
    if raw.endswith("Ki"):
        return int(raw[:-2]) / 1024
    if raw.endswith("Mi"):
        return float(raw[:-2])
    if raw.endswith("Gi"):
        return float(raw[:-2]) * 1024
    if raw.endswith("k"):
        return int(raw[:-1]) * 1000 / (1024 * 1024)
    return float(raw) / (1024 * 1024)


@tool
def top_nodes() -> list[dict[str, Any]]:
    """Return CPU and memory usage for each node via the metrics.k8s.io API.

    Requires metrics-server to be installed in the cluster. Returns an
    empty list with a warning if the API is unavailable (graceful fallback).

    Returns:
        A list of dicts with keys: name, cpu_millicores, memory_mi.
    """
    custom = get_custom_objects()
    try:
        response: dict[str, Any] = custom.list_cluster_custom_object(
            group=_METRICS_GROUP,
            version=_METRICS_VERSION,
            plural=_METRICS_PLURAL,
        )
    except Exception as exc:
        logger.debug(
            "top_nodes: metrics.k8s.io unavailable (%s). "
            "Is metrics-server installed? Returning empty list.",
            exc,
        )
        return []

    results: list[dict[str, Any]] = []
    for item in response.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        usage = item.get("usage", {})
        results.append(
            {
                "name": name,
                "cpu_millicores": round(_parse_cpu_millicores(usage.get("cpu", "0")), 2),
                "memory_mi": round(_parse_mem_mi(usage.get("memory", "0")), 2),
            }
        )

    logger.info("top_nodes returned metrics for %d nodes", len(results))
    return results
