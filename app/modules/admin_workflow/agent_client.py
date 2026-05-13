"""HTTP client for external agent communication.

This module provides the AgentClient class for communicating with:
- Risk Analysis Agent (port 8002) - analyzes disaster risks
- Precautionary Agent (port 8003) - generates precautionary measures

Both agents use the OpenAI Agent SDK framework and expect specific request/response formats.
All communication is asynchronous with proper timeout and error handling.
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentClient:
    """HTTP client for external agent communication.
    
    Handles asynchronous HTTP requests to Risk Analysis Agent and Precautionary Agent
    with proper timeout, error handling, and structured logging.
    
    Requirements: 6.4, 6.6, 8.3, 8.5, 13.2, 13.9, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10
    """

    def __init__(self) -> None:
        """Initialize agent client with URLs from settings."""
        self.risk_analysis_url = settings.RISK_ANALYSIS_AGENT_URL
        self.precautionary_url = settings.PRECAUTIONARY_AGENT_URL
        self.timeout = 60.0  # 60 seconds timeout for long-running agent operations

    async def request_risk_analysis(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send risk analysis request to Risk Analysis Agent.
        
        Args:
            data: Risk analysis request data containing:
                - alert_id: UUID of the threshold alert
                - location: Location data (latitude, longitude, location_name, province)
                - sensor_data: Sensor information (sensor_type, current_value, threshold_value)
                - historical_data: Optional historical data for context
        
        Returns:
            Risk analysis result JSON containing:
                - risk_score: Integer 0-100
                - risk_level: String (LOW, MEDIUM, HIGH, CRITICAL)
                - disaster_type: String (FLOOD, EARTHQUAKE, HEATWAVE, STORM, DROUGHT)
                - affected_area_km2: Float
                - estimated_population_affected: Integer
                - confidence_score: Integer 0-100
                - analysis_summary: String
                - detailed_analysis: Dict with analysis details
                - recommended_actions: List of recommended actions
        
        Raises:
            Exception: On HTTP error, timeout, or connection failure
            
        Requirements: 14.1, 14.4, 14.6, 14.7, 14.8, 14.9, 14.10
        """
        endpoint = f"{self.risk_analysis_url}/api/analyze"
        
        logger.info(
            "Sending risk analysis request to agent",
            extra={
                "agent": "Risk_Analysis_Agent",
                "endpoint": endpoint,
                "alert_id": data.get("alert_id"),
            },
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=data,
                    headers={"Content-Type": "application/json"},
                )
                
                # Raise exception for HTTP errors (4xx, 5xx)
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "Risk analysis request successful",
                    extra={
                        "agent": "Risk_Analysis_Agent",
                        "alert_id": data.get("alert_id"),
                        "risk_level": result.get("risk_level"),
                        "disaster_type": result.get("disaster_type"),
                    },
                )
                
                return result
                
        except httpx.TimeoutException as e:
            logger.error(
                "Risk analysis request timed out",
                extra={
                    "agent": "Risk_Analysis_Agent",
                    "endpoint": endpoint,
                    "timeout_seconds": self.timeout,
                    "alert_id": data.get("alert_id"),
                    "error": str(e),
                },
            )
            raise Exception(
                f"Risk Analysis Agent request timed out after {self.timeout} seconds"
            ) from e
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Risk analysis request failed with HTTP error",
                extra={
                    "agent": "Risk_Analysis_Agent",
                    "endpoint": endpoint,
                    "status_code": e.response.status_code,
                    "alert_id": data.get("alert_id"),
                    "error": str(e),
                },
            )
            raise Exception(
                f"Risk Analysis Agent returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e
            
        except Exception as e:
            logger.error(
                "Risk analysis request failed",
                extra={
                    "agent": "Risk_Analysis_Agent",
                    "endpoint": endpoint,
                    "alert_id": data.get("alert_id"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise Exception(
                f"Risk Analysis Agent communication failed: {str(e)}"
            ) from e

    async def request_precautionary_measures(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send precautionary measures request to Precautionary Agent.
        
        Args:
            data: Precautionary measures request data containing:
                - analysis_id: UUID of the risk analysis
                - risk_analysis_data: Risk analysis results (risk_score, risk_level, disaster_type, etc.)
                - location: Location data (latitude, longitude, location_name, province)
        
        Returns:
            Precautionary measures result JSON containing:
                - overall_strategy: String describing overall strategy
                - measures: List of measure objects with category, action, priority, resources
                - timeline: Dict with phases and durations
                - estimated_cost: Optional float for total estimated cost
        
        Raises:
            Exception: On HTTP error, timeout, or connection failure
            
        Requirements: 14.1, 14.5, 14.6, 14.7, 14.8, 14.9, 14.10
        """
        endpoint = f"{self.precautionary_url}/api/generate-measures"
        
        logger.info(
            "Sending precautionary measures request to agent",
            extra={
                "agent": "Precautionary_Agent",
                "endpoint": endpoint,
                "analysis_id": data.get("analysis_id"),
            },
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=data,
                    headers={"Content-Type": "application/json"},
                )
                
                # Raise exception for HTTP errors (4xx, 5xx)
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "Precautionary measures request successful",
                    extra={
                        "agent": "Precautionary_Agent",
                        "analysis_id": data.get("analysis_id"),
                        "measures_count": len(result.get("measures", [])),
                    },
                )
                
                return result
                
        except httpx.TimeoutException as e:
            logger.error(
                "Precautionary measures request timed out",
                extra={
                    "agent": "Precautionary_Agent",
                    "endpoint": endpoint,
                    "timeout_seconds": self.timeout,
                    "analysis_id": data.get("analysis_id"),
                    "error": str(e),
                },
            )
            raise Exception(
                f"Precautionary Agent request timed out after {self.timeout} seconds"
            ) from e
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Precautionary measures request failed with HTTP error",
                extra={
                    "agent": "Precautionary_Agent",
                    "endpoint": endpoint,
                    "status_code": e.response.status_code,
                    "analysis_id": data.get("analysis_id"),
                    "error": str(e),
                },
            )
            raise Exception(
                f"Precautionary Agent returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e
            
        except Exception as e:
            logger.error(
                "Precautionary measures request failed",
                extra={
                    "agent": "Precautionary_Agent",
                    "endpoint": endpoint,
                    "analysis_id": data.get("analysis_id"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise Exception(
                f"Precautionary Agent communication failed: {str(e)}"
            ) from e


# Singleton instance for use across the application
agent_client = AgentClient()
