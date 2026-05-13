# Agent Client Documentation

## Overview

The `AgentClient` class provides HTTP communication with two external microservices:
1. **Risk Analysis Agent** (port 8002) - Analyzes disaster risks
2. **Precautionary Agent** (port 8003) - Generates precautionary measures

## Configuration

Add the following environment variables to your `.env` file:

```env
# External Agent URLs (for disaster management workflow)
RISK_ANALYSIS_AGENT_URL=http://localhost:8002
PRECAUTIONARY_AGENT_URL=http://localhost:8003
AGENT_API_KEY=default_agent_key_change_in_production
```

## Usage

### Import the Singleton Instance

```python
from app.modules.admin_workflow.agent_client import agent_client
```

### Request Risk Analysis

```python
async def analyze_risk(alert_data):
    try:
        result = await agent_client.request_risk_analysis({
            "alert_id": str(alert.alert_id),
            "location": {
                "latitude": alert.latitude,
                "longitude": alert.longitude,
                "location_name": alert.location_name,
                "province": alert.province,
            },
            "sensor_data": {
                "sensor_type": alert.sensor_type,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
            },
            "historical_data": None,  # Optional
        })
        
        # Result contains:
        # - risk_score (0-100)
        # - risk_level (LOW, MEDIUM, HIGH, CRITICAL)
        # - disaster_type (FLOOD, EARTHQUAKE, HEATWAVE, STORM, DROUGHT)
        # - affected_area_km2
        # - estimated_population_affected
        # - confidence_score (0-100)
        # - analysis_summary
        # - detailed_analysis (dict)
        # - recommended_actions (list)
        
        return result
        
    except Exception as e:
        # Handle timeout, HTTP errors, or connection failures
        logger.error(f"Risk analysis failed: {e}")
        raise
```

### Request Precautionary Measures

```python
async def generate_measures(analysis_data):
    try:
        result = await agent_client.request_precautionary_measures({
            "analysis_id": str(analysis.analysis_id),
            "risk_analysis_data": {
                "risk_score": analysis.risk_score,
                "risk_level": analysis.risk_level,
                "disaster_type": analysis.disaster_type,
                "affected_area_km2": float(analysis.affected_area_km2),
                "estimated_population_affected": analysis.estimated_population_affected,
            },
            "location": {
                "latitude": alert.latitude,
                "longitude": alert.longitude,
                "location_name": alert.location_name,
                "province": alert.province,
            },
        })
        
        # Result contains:
        # - overall_strategy (string)
        # - measures (list of measure objects)
        # - timeline (dict with phases)
        # - estimated_cost (optional float)
        
        return result
        
    except Exception as e:
        # Handle timeout, HTTP errors, or connection failures
        logger.error(f"Precautionary measures generation failed: {e}")
        raise
```

## Error Handling

The agent client handles three types of errors:

1. **Timeout Errors** (`httpx.TimeoutException`)
   - Raised when agent doesn't respond within 60 seconds
   - Logged with agent name and timeout duration

2. **HTTP Status Errors** (`httpx.HTTPStatusError`)
   - Raised when agent returns 4xx or 5xx status codes
   - Logged with status code and response text

3. **Generic Errors** (any other `Exception`)
   - Raised for connection failures or other issues
   - Logged with error type and message

All errors are logged with structured context including:
- Agent name (Risk_Analysis_Agent or Precautionary_Agent)
- Endpoint URL
- Request identifiers (alert_id or analysis_id)
- Error details

## Logging

The agent client uses structured logging for all operations:

```python
logger.info(
    "Sending risk analysis request to agent",
    extra={
        "agent": "Risk_Analysis_Agent",
        "endpoint": endpoint,
        "alert_id": data.get("alert_id"),
    },
)
```

This enables easy filtering and monitoring of agent communication in production.

## Testing

To test the agent client with mocked responses:

```python
from unittest.mock import AsyncMock, patch

async def test_risk_analysis():
    mock_response = {
        "risk_score": 75,
        "risk_level": "HIGH",
        "disaster_type": "FLOOD",
        # ... other fields
    }
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status = lambda: None
        
        result = await agent_client.request_risk_analysis({...})
        
        assert result["risk_score"] == 75
        assert result["risk_level"] == "HIGH"
```

## Requirements Satisfied

This implementation satisfies the following requirements:
- 6.4, 6.6: Risk analysis agent communication
- 8.3, 8.5: Precautionary measures agent communication
- 13.2, 13.9: Error handling and logging
- 14.1-14.10: Agent communication specifications
