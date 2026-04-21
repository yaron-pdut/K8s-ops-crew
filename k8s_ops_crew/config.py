"""Application settings loaded from environment variables via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """K8sOps Crew runtime configuration.

    All fields can be overridden via environment variables or a `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    openai_api_key: str = ""
    supervisor_model: str = "gpt-4o"
    diagnostics_model: str = "gpt-4o-mini"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "k8s-ops-crew"

    # Kubernetes
    kubeconfig: str = ""  # empty → uses default ~/.kube/config

    # Safety
    dry_run: bool = True


# Module-level singleton — import and use directly.
settings = Settings()
