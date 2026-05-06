"""Base agent — shared OpenAI async client, prompt helpers, and retry logic.

All concrete agents inherit from BaseAgent to get a consistent
async OpenAI client, JSON-mode enforcement, and exponential-backoff retries.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Shared OpenAI client (module-level singleton)
# ---------------------------------------------------------------------------

_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return the shared async OpenAI client (lazy init)."""
    global _openai_client  # noqa: PLW0603
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=float(settings.OPENAI_TIMEOUT_SECONDS),
        )
    return _openai_client


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class BaseAgent:
    """Shared behaviour for all ClimaSync AI agents.

    Subclasses only need to provide a system prompt and call
    `self._call_llm(user_prompt, ResponseSchema)` to get a parsed result.
    """

    MODEL: str = ""  # will fall back to settings.OPENAI_MODEL if empty
    MAX_RETRIES: int = 3
    INITIAL_BACKOFF_SECONDS: float = 1.0

    def __init__(self) -> None:
        self._client = get_openai_client()
        self._model = self.MODEL or settings.OPENAI_MODEL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
    ) -> T:
        """Call OpenAI with JSON mode and parse the response into `response_schema`.

        Retries up to MAX_RETRIES times with exponential back-off on transient errors.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    "[%s] LLM call attempt %d/%d model=%s",
                    self.__class__.__name__,
                    attempt,
                    self.MAX_RETRIES,
                    self._model,
                )
                completion = await self._client.chat.completions.create(
                    model=self._model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                raw = completion.choices[0].message.content or "{}"
                parsed: dict[str, Any] = json.loads(raw)
                result = response_schema.model_validate(parsed)
                logger.debug(
                    "[%s] LLM call succeeded on attempt %d",
                    self.__class__.__name__,
                    attempt,
                )
                return result

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                wait = self.INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "[%s] LLM call attempt %d failed: %s — retrying in %.1fs",
                    self.__class__.__name__,
                    attempt,
                    exc,
                    wait,
                )
                if attempt < self.MAX_RETRIES:
                    # asyncio.sleep would be ideal but we do a blocking sleep
                    # here only in the retry path (rarely hit).
                    import asyncio
                    await asyncio.sleep(wait)

        msg = f"[{self.__class__.__name__}] all {self.MAX_RETRIES} LLM attempts failed"
        raise RuntimeError(msg) from last_error

    # ------------------------------------------------------------------
    # Utility: build a compact JSON string suitable for embedding in prompts
    # ------------------------------------------------------------------

    @staticmethod
    def _to_prompt_json(data: Any) -> str:  # noqa: ANN401
        """Serialize `data` to a compact JSON string for embedding in prompts."""
        if isinstance(data, BaseModel):
            return data.model_dump_json(indent=2)
        return json.dumps(data, default=str, indent=2)
