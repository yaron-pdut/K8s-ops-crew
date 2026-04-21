"""Unit tests for Kubernetes read-only tool functions."""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build fake kubernetes API objects
# ---------------------------------------------------------------------------


def _make_pod(
    name: str = "web-abc",
    namespace: str = "default",
    phase: str = "Running",
    restarts: int = 0,
    ready: bool = True,
    node_name: str = "worker-1",
) -> MagicMock:
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.metadata.creation_timestamp = datetime.datetime(2026, 4, 20, 10, 0, 0, tzinfo=datetime.UTC)
    pod.spec.containers = [MagicMock()]
    pod.spec.node_name = node_name
    pod.status.phase = phase
    cs = MagicMock()
    cs.restart_count = restarts
    cs.ready = ready
    pod.status.container_statuses = [cs]
    return pod


def _make_node(
    name: str = "worker-1",
    ready_status: str = "True",
    cpu: str = "4",
    memory: str = "8Gi",
) -> MagicMock:
    node = MagicMock()
    node.metadata.name = name
    node.metadata.labels = {"node-role.kubernetes.io/worker": ""}
    node.metadata.creation_timestamp = datetime.datetime(2026, 4, 19, 0, 0, 0, tzinfo=datetime.UTC)
    cond = MagicMock()
    cond.type = "Ready"
    cond.status = ready_status
    node.status.conditions = [cond]
    node.status.capacity = {"cpu": cpu, "memory": memory}
    node.status.allocatable = {"cpu": cpu, "memory": memory}
    node.status.node_info.kernel_version = "5.15.0"
    node.status.node_info.os_image = "Ubuntu 22.04"
    return node


def _make_event(
    reason: str = "BackOff",
    message: str = "Back-off restarting failed container",
    kind: str = "Pod",
    obj_name: str = "broken-pod",
    count: int = 5,
    namespace: str = "default",
) -> MagicMock:
    evt = MagicMock()
    evt.metadata.name = f"{obj_name}.event"
    evt.metadata.namespace = namespace
    evt.type = "Warning"
    evt.reason = reason
    evt.message = message
    evt.involved_object.kind = kind
    evt.involved_object.name = obj_name
    evt.count = count
    evt.first_timestamp = datetime.datetime(2026, 4, 21, 9, 0, tzinfo=datetime.UTC)
    evt.last_timestamp = datetime.datetime(2026, 4, 21, 10, 0, tzinfo=datetime.UTC)
    evt.event_time = None
    return evt


# ---------------------------------------------------------------------------
# list_pods
# ---------------------------------------------------------------------------


class TestListPods:
    def _patch_core(self, pods: list) -> MagicMock:
        core = MagicMock()
        result = MagicMock()
        result.items = pods
        core.list_pod_for_all_namespaces.return_value = result
        core.list_namespaced_pod.return_value = result
        return core

    def test_returns_all_pods(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_pods import list_pods

        pods = [_make_pod("pod-a"), _make_pod("pod-b", phase="Pending")]
        core = self._patch_core(pods)
        with patch("k8s_ops_crew.tools.list_pods.get_core_v1", return_value=core):
            result = list_pods.invoke({})
        assert len(result) == 2
        assert result[0]["name"] == "pod-a"
        assert result[0]["phase"] == "Running"

    def test_pod_with_restarts(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_pods import list_pods

        pods = [_make_pod("crasher", restarts=7, ready=False)]
        core = self._patch_core(pods)
        with patch("k8s_ops_crew.tools.list_pods.get_core_v1", return_value=core):
            result = list_pods.invoke({})
        assert result[0]["restarts"] == 7
        assert result[0]["ready"] == "0/1"

    def test_api_error_propagates(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_pods import list_pods

        core = MagicMock()
        core.list_pod_for_all_namespaces.side_effect = RuntimeError("API down")
        with patch("k8s_ops_crew.tools.list_pods.get_core_v1", return_value=core):
            with pytest.raises(RuntimeError, match="API down"):
                list_pods.invoke({})

    def test_filtered_by_namespace(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_pods import list_pods

        pods = [_make_pod("ns-pod", namespace="staging")]
        core = self._patch_core(pods)
        with patch("k8s_ops_crew.tools.list_pods.get_core_v1", return_value=core):
            result = list_pods.invoke({"namespace": "staging"})
        core.list_namespaced_pod.assert_called_once_with(namespace="staging")
        assert result[0]["namespace"] == "staging"


# ---------------------------------------------------------------------------
# list_nodes
# ---------------------------------------------------------------------------


class TestListNodes:
    def _patch_core(self, nodes: list) -> MagicMock:
        core = MagicMock()
        result = MagicMock()
        result.items = nodes
        core.list_node.return_value = result
        return core

    def test_returns_nodes(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_nodes import list_nodes

        nodes = [_make_node("cp-1", ready_status="True")]
        core = self._patch_core(nodes)
        with patch("k8s_ops_crew.tools.list_nodes.get_core_v1", return_value=core):
            result = list_nodes.invoke({})
        assert len(result) == 1
        assert result[0]["name"] == "cp-1"
        assert result[0]["ready"] == "True"

    def test_memory_conversion_gi(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_nodes import list_nodes

        nodes = [_make_node("n1", memory="8Gi")]
        core = self._patch_core(nodes)
        with patch("k8s_ops_crew.tools.list_nodes.get_core_v1", return_value=core):
            result = list_nodes.invoke({})
        assert result[0]["memory_capacity_gi"] == pytest.approx(8.0, abs=0.1)

    def test_not_ready_node(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.list_nodes import list_nodes

        nodes = [_make_node("bad-node", ready_status="False")]
        core = self._patch_core(nodes)
        with patch("k8s_ops_crew.tools.list_nodes.get_core_v1", return_value=core):
            result = list_nodes.invoke({})
        assert result[0]["ready"] == "False"


# ---------------------------------------------------------------------------
# get_events
# ---------------------------------------------------------------------------


class TestGetEvents:
    def _patch_core(self, events: list) -> MagicMock:
        core = MagicMock()
        result = MagicMock()
        result.items = events
        core.list_event_for_all_namespaces.return_value = result
        core.list_namespaced_event.return_value = result
        return core

    def test_returns_warning_events_only(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.get_events import get_events

        warning = _make_event()
        normal = MagicMock()
        normal.type = "Normal"
        core = self._patch_core([warning, normal])
        with patch("k8s_ops_crew.tools.get_events.get_core_v1", return_value=core):
            result = get_events.invoke({})
        assert all(e["type"] == "Warning" for e in result)
        assert len(result) == 1

    def test_limit_respected(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.get_events import get_events

        events = [_make_event(obj_name=f"pod-{i}") for i in range(20)]
        core = self._patch_core(events)
        with patch("k8s_ops_crew.tools.get_events.get_core_v1", return_value=core):
            result = get_events.invoke({"limit": 5})
        assert len(result) <= 5

    def test_event_fields(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.get_events import get_events

        core = self._patch_core([_make_event(reason="OOMKilled", count=3)])
        with patch("k8s_ops_crew.tools.get_events.get_core_v1", return_value=core):
            result = get_events.invoke({})
        assert result[0]["reason"] == "OOMKilled"
        assert result[0]["count"] == 3


# ---------------------------------------------------------------------------
# top_nodes
# ---------------------------------------------------------------------------


class TestTopNodes:
    def test_returns_metrics(self, mock_k8s_client) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.top_nodes import top_nodes

        fake_response: dict[str, Any] = {
            "items": [
                {"metadata": {"name": "worker-1"}, "usage": {"cpu": "250m", "memory": "1024Mi"}},
                {"metadata": {"name": "worker-2"}, "usage": {"cpu": "1", "memory": "2Gi"}},
            ]
        }
        custom = MagicMock()
        custom.list_cluster_custom_object.return_value = fake_response
        with patch("k8s_ops_crew.tools.top_nodes.get_custom_objects", return_value=custom):
            result = top_nodes.invoke({})
        assert len(result) == 2
        assert result[0]["cpu_millicores"] == pytest.approx(250.0)
        assert result[0]["memory_mi"] == pytest.approx(1024.0)
        assert result[1]["cpu_millicores"] == pytest.approx(1000.0)
        assert result[1]["memory_mi"] == pytest.approx(2048.0)

    def test_graceful_fallback_when_metrics_unavailable(
        self, mock_k8s_client
    ) -> None:  # noqa: ANN001
        from k8s_ops_crew.tools.top_nodes import top_nodes

        custom = MagicMock()
        custom.list_cluster_custom_object.side_effect = Exception("metrics-server not found")
        with patch("k8s_ops_crew.tools.top_nodes.get_custom_objects", return_value=custom):
            result = top_nodes.invoke({})
        assert result == []
