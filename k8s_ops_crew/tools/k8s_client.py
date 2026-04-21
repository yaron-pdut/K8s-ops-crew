"""Kubernetes client singleton factory.

Loads kubeconfig (in-cluster or from file) once and exposes typed API
client instances for use by all tool functions.
"""

from __future__ import annotations

import logging

from kubernetes import client, config
from kubernetes.client import ApiClient, AppsV1Api, CoreV1Api

from k8s_ops_crew.config import settings

logger = logging.getLogger(__name__)

_api_client: ApiClient | None = None


def _get_api_client() -> ApiClient:
    """Return a shared, lazily-initialised Kubernetes ApiClient."""
    global _api_client  # noqa: PLW0603
    if _api_client is None:
        try:
            # Running inside a cluster (e.g. deployed on K8s itself).
            config.load_incluster_config()
            logger.debug("Loaded in-cluster kubeconfig")
        except config.ConfigException:
            # Running locally — use kubeconfig file.
            kubeconfig = settings.kubeconfig or None
            config.load_kube_config(config_file=kubeconfig)
            logger.debug("Loaded kubeconfig from file: %s", kubeconfig or "~/.kube/config")
        _api_client = ApiClient()
    return _api_client


def get_core_v1() -> CoreV1Api:
    """Return a CoreV1Api client."""
    return CoreV1Api(api_client=_get_api_client())


def get_apps_v1() -> AppsV1Api:
    """Return an AppsV1Api client."""
    return AppsV1Api(api_client=_get_api_client())


def get_custom_objects() -> client.CustomObjectsApi:
    """Return a CustomObjectsApi client (used for metrics.k8s.io)."""
    return client.CustomObjectsApi(api_client=_get_api_client())


def reset_client() -> None:
    """Reset the cached client — useful in tests."""
    global _api_client  # noqa: PLW0603
    _api_client = None
