"""Shared pytest fixtures for K8sOps Crew tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fake Kubernetes data
# ---------------------------------------------------------------------------

FAKE_POD = {
    "name": "web-6d8f4b7c9-abc12",
    "namespace": "default",
    "phase": "Running",
    "ready": "1/1",
    "restarts": 0,
    "node": "worker-1",
    "age_seconds": 3600.0,
}

FAKE_POD_CRASHLOOP = {
    "name": "broken-pod-xyz",
    "namespace": "staging",
    "phase": "CrashLoopBackOff",
    "ready": "0/1",
    "restarts": 12,
    "node": "worker-2",
    "age_seconds": 7200.0,
}

FAKE_NODE = {
    "name": "worker-1",
    "ready": "True",
    "roles": ["worker"],
    "cpu_capacity": "4",
    "memory_capacity_gi": 7.76,
    "cpu_allocatable": "4",
    "memory_allocatable_gi": 7.26,
    "kernel_version": "5.15.0",
    "os_image": "Ubuntu 22.04",
    "age_seconds": 86400.0,
}

FAKE_EVENT = {
    "namespace": "staging",
    "name": "broken-pod-xyz.event1",
    "reason": "BackOff",
    "message": "Back-off restarting failed container",
    "involved_object_kind": "Pod",
    "involved_object_name": "broken-pod-xyz",
    "count": 12,
    "first_time": "2026-04-20T10:00:00",
    "last_time": "2026-04-21T10:00:00",
    "type": "Warning",
}

FAKE_METRIC = {
    "name": "worker-1",
    "cpu_millicores": 250.0,
    "memory_mi": 1024.0,
}

FAKE_SNAPSHOT: dict[str, Any] = {
    "pods": [FAKE_POD, FAKE_POD_CRASHLOOP],
    "nodes": [FAKE_NODE],
    "events": [FAKE_EVENT],
    "node_metrics": [FAKE_METRIC],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_k8s_client():
    """Patch kubernetes.config so no real kubeconfig is needed."""
    with (
        patch("kubernetes.config.load_incluster_config", side_effect=Exception("not in cluster")),
        patch("kubernetes.config.load_kube_config"),
        patch("kubernetes.client.ApiClient"),
    ):
        yield


@pytest.fixture()
def mock_list_pods():
    """Patch list_pods tool to return deterministic data."""
    with patch(
        "k8s_ops_crew.tools.list_pods.list_pods",
        return_value=[FAKE_POD, FAKE_POD_CRASHLOOP],
    ) as m:
        yield m


@pytest.fixture()
def mock_list_nodes():
    """Patch list_nodes tool to return deterministic data."""
    with patch(
        "k8s_ops_crew.tools.list_nodes.list_nodes",
        return_value=[FAKE_NODE],
    ) as m:
        yield m


@pytest.fixture()
def mock_get_events():
    """Patch get_events tool to return deterministic data."""
    with patch(
        "k8s_ops_crew.tools.get_events.get_events",
        return_value=[FAKE_EVENT],
    ) as m:
        yield m


@pytest.fixture()
def mock_top_nodes():
    """Patch top_nodes tool to return deterministic data."""
    with patch(
        "k8s_ops_crew.tools.top_nodes.top_nodes",
        return_value=[FAKE_METRIC],
    ) as m:
        yield m


@pytest.fixture()
def fake_snapshot() -> dict[str, Any]:
    """Return a pre-built cluster snapshot dict."""
    return FAKE_SNAPSHOT.copy()


@pytest.fixture()
def mock_llm():
    """Return a MagicMock that mimics a LangChain ChatModel."""
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    return llm
