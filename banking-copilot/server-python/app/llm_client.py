"""
LLM client factory.

The agent code never hard-codes a provider. It calls get_llm() which reads
LLM_PROVIDER from the environment and returns a ready (client, model) pair that
speaks the OpenAI API shape. Azure AI Foundry deployments and OpenAI both use
that same shape, so switching is one env var.

Env (Foundry / Azure OpenAI — the default, LLM_PROVIDER=foundry or azure):
    AZURE_OPENAI_ENDPOINT      https://<your-project>.openai.azure.com/
    AZURE_OPENAI_API_KEY       <key from the deployment page>  (optional)
    AZURE_OPENAI_DEPLOYMENT    <your model deployment name, e.g. gpt-4o>
    AZURE_OPENAI_API_VERSION   e.g. 2024-08-01-preview

Two ways to authenticate to a Foundry deployment:
  1. API key   — set AZURE_OPENAI_API_KEY. Simple, but many corp tenants
                 disable it (keyless-only policy).
  2. Keyless   — leave AZURE_OPENAI_API_KEY empty. We then use your own Azure
                 identity (DefaultAzureCredential): run `az login` once and your
                 signed-in user is the credential. More secure, no secret in .env.
                 Your identity needs the "Cognitive Services OpenAI User" role on
                 the resource (usually auto-granted to the creator).

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

        endpoint = _require("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if api_key:
            # Path 1: API-key auth.
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            # Path 2: keyless — use the caller's Azure identity (az login / MSI).
            try:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )
            except ImportError as exc:  # pragma: no cover
                raise LLMConfigError(
                    "Keyless auth needs the azure-identity package. "
                    "Install it: pip install azure-identity"
                ) from exc

            # If the resource lives in a different tenant than your default az
            # subscription (common with MCAP / sandbox subs), pin it so the CLI
            # fetches a token from the right directory. On Azure (managed
            # identity) leave AZURE_TENANT_ID unset — MI is single-tenant.
            tenant = os.getenv("AZURE_TENANT_ID")
            if tenant:
                from azure.identity import AzureCliCredential

                credential = AzureCliCredential(tenant_id=tenant)
            else:
                credential = DefaultAzureCredential()

            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=api_version,
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
