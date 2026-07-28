"""
LLM client factory.

The agent code never hard-codes a provider. It calls get_llm() which reads
LLM_PROVIDER from the environment and returns a ready (client, model) pair that
speaks the OpenAI API shape. Azure AI Foundry deployments and OpenAI both use
that same shape, so switching is one env var.

Env (Foundry / Azure OpenAI — the default, LLM_PROVIDER=foundry or azure):
    AZURE_OPENAI_ENDPOINT      https://<your-project>.openai.azure.com/
    AZURE_OPENAI_API_KEY       <key from the deployment page>
    AZURE_OPENAI_DEPLOYMENT    <your model deployment name, e.g. gpt-4o>
    AZURE_OPENAI_API_VERSION   e.g. 2024-08-01-preview

Env (plain OpenAI fallback — LLM_PROVIDER=openai):
    OPENAI_API_KEY             <your OpenAI key>
    OPENAI_MODEL               e.g. gpt-4o
"""
from __future__ import annotations

import os


class LLMConfigError(RuntimeError):
    """Raised when required provider settings are missing."""


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise LLMConfigError(
            f"Missing required environment variable {name}. "
            f"Copy .env.example to .env and fill in your Foundry settings."
        )
    return val


def get_llm():
    """Return (client, model_name) for the configured provider."""
    provider = os.getenv("LLM_PROVIDER", "foundry").strip().lower()

    if provider in ("foundry", "azure", "azure_openai"):
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=_require("AZURE_OPENAI_ENDPOINT"),
            api_key=_require("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
        # For Azure, the "model" passed to the API is the *deployment name*.
        model = _require("AZURE_OPENAI_DEPLOYMENT")
        return client, model

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=_require("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return client, model

    raise LLMConfigError(
        f"Unknown LLM_PROVIDER '{provider}'. Use 'foundry' (default) or 'openai'."
    )
