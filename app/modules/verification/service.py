"""AI-powered Verification Agent service.

Uses GPT-4o (vision-capable) to analyze images, videos, or text for
disaster content authenticity. Supports:
  - Image files (jpg, png, webp, gif)
  - Video frames (first frame extracted via URL or base64)
  - Plain text reports
  - Mixed (image + descriptive text)
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.modules.verification.schemas import (
    VerificationResult,
    VerificationSignal,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are ClimaSync.AI's Disaster Content Verification Specialist — an expert forensic analyst with deep knowledge of:
- Disaster photography and videography patterns
- Image manipulation detection (splicing, deepfakes, metadata inconsistencies)
- Pakistan's disaster-prone geography, seasonal patterns, and typical disaster scenarios
- Social media misinformation tactics during emergencies
- Linguistic markers of authentic vs. fabricated eyewitness accounts

Your task: Analyze submitted content (images, video frames, or text) and determine its authenticity as disaster-related evidence.

ALWAYS respond with ONLY valid JSON matching this exact schema:
{
  "verdict": "authentic" | "likely_authentic" | "uncertain" | "likely_manipulated" | "manipulated",
  "confidence": <float 0.0-1.0>,
  "authenticity_score": <float 0.0-10.0>,
  "content_type": "image" | "video" | "text" | "mixed",
  "disaster_relevance": "high" | "medium" | "low" | "not_disaster_related",
  "supporting_signals": [
    {"label": "...", "detail": "...", "weight": "strong"|"moderate"|"weak", "supports_authentic": true}
  ],
  "red_flags": [
    {"label": "...", "detail": "...", "weight": "strong"|"moderate"|"weak", "supports_authentic": false}
  ],
  "summary": "<2-3 sentence plain-language verdict>",
  "recommended_action": "approve_and_alert" | "flag_for_human_review" | "reject_as_misinformation" | "request_more_info",
  "reasoning": "<detailed analysis chain>"
}"""


class VerificationAgent:
    """Multimodal verification agent using GPT-4o vision capabilities."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
        self._model = "gpt-4o"  # Must use 4o for vision

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def verify_text(self, text: str, context: str | None = None) -> VerificationResult:
        """Verify a plain text report."""
        user_content = f"TEXT CONTENT TO VERIFY:\n\n{text}"
        if context:
            user_content += f"\n\nCONTEXT PROVIDED BY SUBMITTER: {context}"
        return await self._run_verification(user_content, [])

    async def verify_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        caption: str | None = None,
    ) -> VerificationResult:
        """Verify an image (JPEG, PNG, WEBP, GIF)."""
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_part: dict[str, Any] = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
        }
        text_part = caption or "Analyze this image for disaster content authenticity."
        return await self._run_verification(text_part, [image_part])

    async def verify_mixed(
        self,
        image_bytes: bytes | None,
        mime_type: str | None,
        text: str,
    ) -> VerificationResult:
        """Verify image + accompanying text together."""
        extra_parts: list[dict[str, Any]] = []
        if image_bytes and mime_type:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            extra_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
            })
        return await self._run_verification(text, extra_parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_verification(
        self,
        text_content: str,
        extra_parts: list[dict[str, Any]],
    ) -> VerificationResult:
        """Send content to GPT-4o and parse the structured result."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_content},
                    *extra_parts,
                ],
            },
        ]

        logger.info("[VerificationAgent] Sending content to GPT-4o for analysis")

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temp = more deterministic analysis
            max_tokens=2000,
        )

        raw_json = response.choices[0].message.content or "{}"
        logger.info("[VerificationAgent] Received GPT-4o response (%d chars)", len(raw_json))

        return self._parse_result(raw_json)

    def _parse_result(self, raw_json: str) -> VerificationResult:
        """Parse and validate the LLM JSON response."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.error("[VerificationAgent] JSON parse failed: %s", exc)
            # Return a safe fallback
            return VerificationResult(
                verdict="uncertain",
                confidence=0.0,
                authenticity_score=5.0,
                content_type="text",
                disaster_relevance="low",
                supporting_signals=[],
                red_flags=[],
                summary="Verification could not be completed due to a parsing error.",
                recommended_action="flag_for_human_review",
                reasoning=f"JSON parse error: {exc}",
            )

        # Parse signal lists
        supporting = [
            VerificationSignal(**s)
            for s in data.get("supporting_signals", [])
            if isinstance(s, dict)
        ]
        red_flags = [
            VerificationSignal(**r)
            for r in data.get("red_flags", [])
            if isinstance(r, dict)
        ]

        return VerificationResult(
            verdict=data.get("verdict", "uncertain"),
            confidence=float(data.get("confidence", 0.5)),
            authenticity_score=float(data.get("authenticity_score", 5.0)),
            content_type=data.get("content_type", "text"),
            disaster_relevance=data.get("disaster_relevance", "low"),
            supporting_signals=supporting,
            red_flags=red_flags,
            summary=data.get("summary", ""),
            recommended_action=data.get("recommended_action", "flag_for_human_review"),
            reasoning=data.get("reasoning", ""),
        )
