"""LLM call logging utilities."""

import datetime
from pathlib import Path

# Path relative to this module so the log lands in the project root on disk.
LOG_PATH = Path(__file__).resolve().parent / "llm_calls.log"


def log_llm_call(provider: str, model: str, tokens: int) -> None:
    """Append a single LLM invocation line to ``llm_calls.log``.

    Args:
        provider: The inference provider, e.g. ``"openrouter"`` or ``"groq"``.
        model: The model identifier, e.g. ``"llama-3.3-70b-versatile"``.
        tokens: Total tokens consumed by the call (accepted as ``int``).
    """
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} | "
            f"{provider} | {model} | {int(tokens)} tokens\n"
        )