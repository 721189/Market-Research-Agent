"""Cost-aware LLM routing.

Picks a provider + model per task type so expensive calls (financials,
launch brief) go to the capable model while cheap calls (web scrape) use
the small one. OpenRouter is the primary provider; Groq is the fallback
when the OpenRouter key is missing. Batch mode targets the DeepInfra batch
API and gracefully falls back to Groq deep when the key is unset.

Clients are built lazily so importing this module never crashes when a key
is absent.
"""

import os
from typing import Optional

from openai import OpenAI

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter rotates its free-tier models frequently. Override these in .env
# when a free slug disappears instead of editing code:
#   OPENROUTER_SCRAPE_MODEL=openrouter/<vendor>/<model>:free
#   OPENROUTER_DEEP_MODEL=openrouter/<vendor>/<model>:free
_OPENROUTER_SCRAPE_MODEL = os.getenv(
    "OPENROUTER_SCRAPE_MODEL", "openrouter/nvidia/nemotron-3.5-lightning:free"
)
_OPENROUTER_DEEP_MODEL = os.getenv(
    "OPENROUTER_DEEP_MODEL", "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Route -> (provider, model).
# OpenRouter uses natively-supported provider prefix in CrewAI's LLM class,
# which auto-resolves the base URL, API key, and required headers.
# The lightning model handles cheap scraping; the 120B model handles financials/writes.
# Groq fallback models keep the openai/ prefix (OpenAI-compat workaround).
_MODE_BY_TASK_TYPE: dict[str, tuple[str, str]] = {
    "scrape": ("openrouter", _OPENROUTER_SCRAPE_MODEL),   # cheaper for scraping
    "financial": ("openrouter", _OPENROUTER_DEEP_MODEL),  # better for numbers
    "product": ("openrouter", _OPENROUTER_DEEP_MODEL),    # better for writing
    "quick": ("openrouter", _OPENROUTER_SCRAPE_MODEL),
    "deep": ("openrouter", _OPENROUTER_DEEP_MODEL),
    "batch": ("deepinfra", "deepinfra/meta-llama/Meta-Llama-3.1-70B-Instruct"),
}

# Groq fallback model used when a preferred provider key is missing.
_GROQ_FALLBACK_DEEP = "openai/llama-3.3-70b-versatile"
_GROQ_FALLBACK_QUICK = "openai/llama-3.1-8b-instant"


def get_model_for_task(task_type: str) -> str:
    """Return the model identifier used for a task type (default = deep).

    Args:
        task_type: One of ``scrape``, ``financial``, ``product``, ``quick``,
            ``deep`` or ``batch``.

    Returns:
        The model name (without any API-shape prefix).
    """
    provider, model = _MODE_BY_TASK_TYPE.get(task_type, _MODE_BY_TASK_TYPE["deep"])
    # Strip the LiteLLM/LiteLLM provider prefix for a clean model identifier.
    return model.split("/", 1)[1] if "/" in model else model


def get_llm_config(task_type: str) -> dict[str, str]:
    """Return provider-specific connection details for CrewAI's ``LLM``.

    Falls back to Groq when a requested provider key is missing so the
    app never crashes on an unconfigured optional provider.

    Returns:
        A dict with ``model`` (with the LiteLLM prefix), ``base_url`` and
        ``api_key`` suitable for ``LLM(**cfg)``.
    """
    provider, model = _MODE_BY_TASK_TYPE.get(task_type, _MODE_BY_TASK_TYPE["deep"])

    # Resolve base URL + API key per provider, with Groq fallback chains.
    if provider == "openrouter" and OPENROUTER_API_KEY:
        base_url = OPENROUTER_BASE_URL
        api_key = OPENROUTER_API_KEY
    elif provider == "deepinfra" and DEEPINFRA_API_KEY:
        base_url = DEEPINFRA_BASE_URL
        api_key = DEEPINFRA_API_KEY
    else:  # groq (either groq itself or a fallback from openrouter/deepinfra)
        base_url = GROQ_BASE_URL
        api_key = GROQ_API_KEY
        # If the requested provider key was missing, use the Groq fallback model.
        if provider != "groq":
            model = _GROQ_FALLBACK_DEEP

    return {
        "model": model,
        "base_url": base_url,
        "api_key": api_key or "",
    }


def _build_client(base_url: str, api_key: Optional[str]) -> Optional[OpenAI]:
    if not api_key:
        return None
    return OpenAI(base_url=base_url, api_key=api_key)


# Clients for direct OpenAI-compatible calls (e.g. DeepInfra batch usage).
GROQ_CLIENT = _build_client(GROQ_BASE_URL, GROQ_API_KEY)
DEEPINFRA_CLIENT = _build_client(DEEPINFRA_BASE_URL, DEEPINFRA_API_KEY)
OPENROUTER_CLIENT = _build_client(OPENROUTER_BASE_URL, OPENROUTER_API_KEY)
