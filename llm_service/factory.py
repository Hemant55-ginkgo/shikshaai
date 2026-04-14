# llm_service/factory.py
# BRAIN layer — constructs the right brain based on config.py
# Decision 10 — Model switch flag via config.py
#
# app.py calls: get_primary_brain(api_key) and get_escalation_brain(api_key)
# Nothing in app.py knows which model class is being used.
# Switching MODEL_BACKEND in config.py is the only change needed to swap brains.

import config
from llm_service.base import BaseLLM


def get_primary_brain(api_key: str) -> BaseLLM:
    """
    Returns the primary brain for standard generation.
    Controlled by config.MODEL_BACKEND.
    """
    backend = config.MODEL_BACKEND

    if backend == "claude":
        from llm_service.claude import ClaudeHaiku
        return ClaudeHaiku(api_key=api_key)

    if backend == "gemini":
        # Placeholder — implement llm_service/gemini.py when ready
        raise NotImplementedError(
            "Gemini backend not yet implemented. "
            "Create llm_service/gemini.py implementing BaseLLM."
        )

    if backend == "local":
        # Placeholder — implement llm_service/ollama.py when ready
        raise NotImplementedError(
            "Local backend not yet implemented. "
            "Create llm_service/ollama.py implementing BaseLLM."
        )

    raise ValueError(
        f"Unknown MODEL_BACKEND '{backend}' in config.py. "
        f"Valid values: 'claude' | 'gemini' | 'local'"
    )


def get_escalation_brain(api_key: str) -> BaseLLM:
    """
    Returns the escalation brain used silently when primary fails after retry.
    Decision 5 — repair → retry → escalate → fail clean.
    Always Claude Sonnet regardless of MODEL_BACKEND.
    If backend is local, escalation still goes to Sonnet (requires API key).
    """
    from llm_service.claude import ClaudeSonnet
    return ClaudeSonnet(api_key=api_key)
