"""Pydantic schemas for the AI Verification Agent.

Handles request/response types for image, video, and text authenticity analysis.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TextVerificationRequest(BaseModel):
    """Request body for text-only verification."""
    text: str = Field(..., min_length=10, max_length=10000, description="Text content to verify")
    context: str | None = Field(None, description="Optional context (location, date, event name)")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class VerificationSignal(BaseModel):
    """A single evidence signal supporting or opposing authenticity."""
    label: str
    detail: str
    weight: Literal["strong", "moderate", "weak"]
    supports_authentic: bool  # True = supports real, False = supports fake/manipulated


class VerificationResult(BaseModel):
    """Full result returned by the Verification Agent."""

    verdict: Literal["authentic", "likely_authentic", "uncertain", "likely_manipulated", "manipulated"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0–1")
    authenticity_score: float = Field(ge=0.0, le=10.0, description="10 = fully authentic, 0 = clear fake")

    # Content classification
    content_type: Literal["image", "video", "text", "mixed"]
    disaster_relevance: Literal["high", "medium", "low", "not_disaster_related"]

    # Evidence
    supporting_signals: list[VerificationSignal] = Field(default_factory=list)
    red_flags: list[VerificationSignal] = Field(default_factory=list)

    # Summary
    summary: str = Field(description="Human-readable 2-3 sentence analysis summary")
    recommended_action: Literal[
        "approve_and_alert",
        "flag_for_human_review",
        "reject_as_misinformation",
        "request_more_info",
    ]
    reasoning: str = Field(description="Detailed LLM reasoning chain")
