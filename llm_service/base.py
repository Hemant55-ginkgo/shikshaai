# llm_service/base.py
# BRAIN layer — abstract interface
# Decision 2 — Extract prompt logic into llm_service/
#
# Every brain (Claude, Gemini, local) must implement this interface.
# app.py and validator.py depend only on this — never on claude.py directly.
# Swapping the brain = adding a new file that implements BaseLLM. Nothing else changes.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMUsage:
    """Token usage returned alongside every generation. Logged to Supabase sessions table."""
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def estimated_cost_usd(self) -> float:
        """
        Haiku pricing as baseline. Override in subclass if backend has different rates.
        claude.py overrides this with exact Haiku rates including cache discount.
        """
        return (
            (self.input_tokens * 0.0000008)
            + (self.output_tokens * 0.000001)
            + (self.cache_read_tokens * 0.00000008)
        )


@dataclass
class LLMResponse:
    """Everything returned from a single model call."""
    raw_text: str        # unparsed model output — logged to Supabase as raw_model_output
    usage: LLMUsage
    model_id: str        # exact model string used — logged to sessions table


class BaseLLM(ABC):
    """
    Abstract interface for all LLM backends.
    Implementations live in llm_service/claude.py, gemini.py, ollama.py.
    """

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Single generation call.
        Returns LLMResponse with raw text — parsing happens in validator.py.
        Raises on network/auth error — validator.py handles recovery.
        """
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Exact model string — logged to Supabase sessions table."""
        ...

    @property
    @abstractmethod
    def prompt_tier(self) -> str:
        """
        Which prompt tier this brain uses.
        "standard" → Haiku / Sonnet
        "compact"  → local / LLaMA
        Maps to SYSTEM_PROMPTS keys in contract/prompts.py
        """
        ...
