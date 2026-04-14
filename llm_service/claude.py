# llm_service/claude.py
# BRAIN layer — Claude (Haiku + Sonnet) implementation
# Decision 2 — app.py never imports anthropic directly
#
# API key is passed in at construction — never fetched here.
# st.secrets lives in app.py only. This file has no Streamlit dependency.

import anthropic

from llm_service.base import BaseLLM, LLMResponse, LLMUsage


# ── Model strings ────────────────────────────────────────────────────────────

HAIKU_MODEL  = "claude-haiku-4-5-20251001"   # primary — fast, cheap, cached
SONNET_MODEL = "claude-sonnet-4-6"            # escalation only (Decision 5)


# ── Haiku brain (primary) ────────────────────────────────────────────────────

class ClaudeHaiku(BaseLLM):
    """
    Primary brain. Used for all standard generations.
    System prompt is prompt-cached — ~90% cheaper on repeat calls.
    """

    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def model_id(self) -> str:
        return HAIKU_MODEL

    @property
    def prompt_tier(self) -> str:
        return "standard"

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 500,
    ) -> LLMResponse:
        message = self._client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},  # prompt caching
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        usage = LLMUsage(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            cache_read_tokens=getattr(message.usage, "cache_read_input_tokens", 0),
            cache_creation_tokens=getattr(message.usage, "cache_creation_input_tokens", 0),
        )

        return LLMResponse(
            raw_text=message.content[0].text.strip(),
            usage=usage,
            model_id=self.model_id,
        )


# ── Sonnet brain (escalation only) ───────────────────────────────────────────

class ClaudeSonnet(BaseLLM):
    """
    Escalation brain. Used silently when Haiku fails after repair + retry.
    Teacher sees "Taking a little longer..." — never knows a different model ran.
    Decision 5 — repair → retry → escalate → fail clean.
    """

    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def model_id(self) -> str:
        return SONNET_MODEL

    @property
    def prompt_tier(self) -> str:
        return "standard"   # same prompt tier as Haiku

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 600,   # slightly more headroom for escalation
    ) -> LLMResponse:
        message = self._client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        usage = LLMUsage(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            cache_read_tokens=getattr(message.usage, "cache_read_input_tokens", 0),
            cache_creation_tokens=getattr(message.usage, "cache_creation_input_tokens", 0),
        )

        return LLMResponse(
            raw_text=message.content[0].text.strip(),
            usage=usage,
            model_id=self.model_id,
        )
