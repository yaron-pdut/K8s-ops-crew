"""LLM provider factory for K8sOps Crew.

Supports three providers, selected via the ``LLM_PROVIDER`` env var:
- ``openai``  — OpenAI API (default, requires OPENAI_API_KEY)
- ``azure``   — Azure OpenAI Service (requires AZURE_OPENAI_* vars)
- ``ollama``  — Local Ollama server (no API key, no internet)
"""

from __future__ import annotations

import logging
from typing import Any

from k8s_ops_crew.config import settings

logger = logging.getLogger(__name__)


def get_llm(model_override: str | None = None, tools: list | None = None) -> Any:
    """Return a configured LangChain chat model for the active provider.

    Args:
        model_override: Override the default model name from settings.
        tools: If provided, bind these tools to the LLM via ``bind_tools``.

    Returns:
        A LangChain ``BaseChatModel`` instance, optionally with tools bound.
    """
    provider = settings.llm_provider.lower()
    logger.info("LLM provider: %s", provider)

    if provider == "ollama":
        llm = _build_ollama(model_override)
    elif provider == "azure":
        llm = _build_azure(model_override)
    else:
        llm = _build_openai(model_override)

    if tools:
        llm = llm.bind_tools(tools)

    return llm


def _build_openai(model_override: str | None) -> Any:
    from langchain_openai import ChatOpenAI

    model = model_override or settings.supervisor_model
    logger.debug("OpenAI model: %s", model)
    return ChatOpenAI(model=model, temperature=0)


def _build_azure(model_override: str | None) -> Any:
    from langchain_openai import AzureChatOpenAI

    deployment = model_override or settings.azure_openai_deployment_name
    logger.debug("Azure OpenAI deployment: %s", deployment)
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,  # type: ignore[arg-type]
        api_version=settings.azure_openai_api_version,
        azure_deployment=deployment,
        temperature=0,
    )


def _build_ollama(model_override: str | None) -> Any:
    from langchain_ollama import ChatOllama

    model = model_override or settings.ollama_model
    logger.debug("Ollama model: %s @ %s", model, settings.ollama_base_url)
    return ChatOllama(
        model=model,
        base_url=settings.ollama_base_url,
        temperature=0,
        # Ask Ollama to return JSON so structured-output parsing is reliable.
        format="json",
    )
