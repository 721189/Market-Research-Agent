"""Cost-aware LLM routing.

Picks a provider + model per task type so expensive calls (financials,
launch brief) go to the capable model while cheap calls (web scrape) use
the small one. Batch mode targets the DeepInfra batch API and gracefully
falls back to Groq when the optional key is missing.

Clients are built lazily so importing this module never crashes when a key
is absent.
"""

import os
from typing import Optional

from openai import OpenAI

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"

# Route -> (provider, model). Groq model names keep the "openai/" LiteLLM
# prefix used elsewhere in the project (OpenAI-compatibility workaround).
_MODE_BY_TASK_TYPE: dict[str, tuple[str, str]] = {
    "scrape": ("groq", "openai/llama-3.1-8b-instant"),  # cheaper for scraping
    "financial": ("groq", "openai/llama-3.3-70b-versatile"),  # better for numbers
    "product": ("groq", "openai/llama-3.3-70b-versatile"),
    "quick": ("groq", "openai/llama-3.1-8b-instant"),
    "deep": ("groq", "openai/llama-3.3-70b-versatile"),
    "batch": ("deepinfra", "deepinfra/meta-llama/Meta-Llama-3.1-70B-Instruct"),
}


def get_model_for_task(task_type: str) -> str:
    """Return the model identifier used for a task type (default = deep).

    Args:
        task_type: One of ``scrape``, ``financial``, ``product``, ``quick``,
            ``deep`` or ``batch``.

    Returns:
        The model name (without any API-shape prefix).
    """
    provider, model = _MODE_BY_TASK_TYPE.get(task_type, _MODE_BY_TASK_TYPE["deep"])
    # Strip the LiteLLM provider prefix for a clean model identifier.
    return model.split("/", 1)[1] if "/" in model else model


def get_llm_config(task_type: str) -> dict[str, str]:
    """Return provider-specific connection details for CrewAI's ``LLM``.

    Falls back to Groq deep when a requested provider key is missing so the
    app never crashes on an unconfigured optional provider.

    Returns:
        A dict with ``model`` (with the LiteLLM prefix), ``base_url`` and
        ``api_key`` suitable for ``LLM(**cfg)``.
    """
    provider, model = _MODE_BY_TASK_TYPE.get(task_type, _MODE_BY_TASK_TYPE["deep"])
    if provider == "deepinfra":
        if not DEEPINFRA_API_KEY:
            provider, model = _MODE_BY_TASK_TYPE["deep"]
        return {
            "model": model,
            "base_url": DEEPINFRA_BASE_URL,
            "api_key": DEEPINFRA_API_KEY or GROQ_API_KEY or "",
        }
    return {
        "model": model,
        "base_url": GROQ_BASE_URL,
        "api_key": GROQ_API_KEY or "",
    }


def _build_client(base_url: str, api_key: Optional[str]) -> Optional[OpenAI]:
    if not api_key:
        return None
    return OpenAI(base_url=base_url, api_key=api_key)


# Clients for direct OpenAI-compatible calls (e.g. DeepInfra batch usage).
GROQ_CLIENT = _build_client(GROQ_BASE_URL, GROQ_API_KEY)
DEEPINFRA_CLIENT = _build_client(DEEPINFRA_BASE_URL, DEEPINFRA_API_KEY)