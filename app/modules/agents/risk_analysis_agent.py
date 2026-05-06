"""Risk Analysis Agent — Agent 2 of the ClimaSync AI pipeline.

Receives a DisasterContext and produces a RiskReport by calling OpenAI
in JSON mode. Also writes the risk_level and severity_score back to the
disaster_events table.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.base_agent import BaseAgent
from app.modules.agents.schemas import DisasterContext, RiskReport
from app.modules.disasters.models import DisasterEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — stored as a module constant for easy tuning
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior disaster risk analyst for Pakistan's National Disaster Management Authority (NDMA).

Given structured data about a disaster event — including its type, location, affected population, live weather, and sensor readings — your job is to:
1. Classify the risk level: "low", "medium", "high", or "critical"
2. Assign a severity score from 0.0 (negligible) to 10.0 (catastrophic)
3. Estimate the affected population
4. Identify the key risk factors driving the classification
5. Recommend the response window in hours (how quickly teams must mobilise)
6. Express your confidence level (0.0–1.0)
7. Provide a concise reasoning paragraph

Context about Pakistan:
- Densely populated flood plains along Indus River basin (Punjab, Sindh)
- Earthquake-prone regions: KPK, Balochistan, AJK, Gilgit-Baltistan
- Flash-flood risk in mountain valleys: Chitral, Dir, Swat, parts of KPK
- Urban heat-island heatwave risk in Karachi, Lahore during summer months
- Population density hotspots: Karachi (14M), Lahore (13M), Faisalabad (4M)

IMPORTANT: You MUST return a valid JSON object matching this exact schema — no extra keys, no markdown:
{
  "risk_level": "low" | "medium" | "high" | "critical",
  "severity_score": <float 0.0-10.0>,
  "affected_population_estimate": <integer>,
  "estimated_damage_pkr": <integer or null>,
  "key_risk_factors": ["...", "..."],
  "recommended_response_window_hours": <integer>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<string>"
}"""


class RiskAnalysisAgent(BaseAgent):
    """Classifies disaster risk and estimates impact using OpenAI."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__()
        self._db = db

    async def run(self, context: DisasterContext) -> RiskReport:
        """Analyse context and return a RiskReport. Also persists to DB."""
        logger.info(
            "[RiskAnalysisAgent] analysing event_id=%s type=%s",
            context.event_id,
            context.event_type,
        )

        user_prompt = self._build_prompt(context)
        report = await self._call_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=RiskReport,
        )

        await self._persist(context.event_id, report)

        logger.info(
            "[RiskAnalysisAgent] result: risk_level=%s severity=%.1f confidence=%.2f",
            report.risk_level,
            report.severity_score,
            report.confidence,
        )
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, context: DisasterContext) -> str:
        ngo_summary = (
            f"{len(context.nearby_ngos)} verified NGOs within operational range"
            if context.nearby_ngos
            else "No verified NGOs found nearby"
        )

        return f"""Analyse the following disaster event and return a RiskReport JSON.

## Disaster Event
- Event ID: {context.event_id}
- Type: {context.event_type}
- Title: {context.title}
- Location: {context.location_name or "Unknown"}, {context.district or "Unknown District"}, {context.province or "Unknown Province"}, Pakistan
- Coordinates: lat={context.latitude:.4f}, lon={context.longitude:.4f}
- Detected at: {context.detected_at.isoformat()}
- Reported severity score: {context.severity_score or "not set"}
- Reported affected population: {context.affected_population or "unknown"}

## Live Weather at Event Location
{self._to_prompt_json(context.weather_summary)}

## Sensor / Environmental Readings
{self._to_prompt_json(context.sensor_readings)}

## Response Capacity
{ngo_summary}

## Source Alert Details
{self._to_prompt_json(context.raw_event.get("source_alert") or {})}

Produce the RiskReport JSON now."""

    async def _persist(self, event_id: uuid.UUID, report: RiskReport) -> None:
        """Write risk_level, severity_score, and analyzed_at back to the DB."""
        stmt = (
            update(DisasterEvent)
            .where(DisasterEvent.event_id == event_id)
            .values(
                risk_level=report.risk_level,
                severity_score=round(report.severity_score, 1),
                analyzed_at=datetime.now(timezone.utc),
            )
        )
        await self._db.execute(stmt)
        await self._db.commit()
        logger.debug("[RiskAnalysisAgent] DB updated for event_id=%s", event_id)
