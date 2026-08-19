# ClimaSync Risk Analysis Agent - API Integration Guide

This document explains how the main ClimaSync backend (or any other service) should interact with the **Risk Analysis Agent**. It covers the required request data, the API authentication, the agent's internal workflow, and the expected structured output.

## 1. Available APIs

The service exposes the following main endpoint:

### `POST /api/v1/assess`
- **Purpose**: Triggers the Risk Analysis Agent to analyze a specific disaster "breach" (e.g., a river crossing a danger threshold or an earthquake occurring).
- **Authentication**: Requires a custom header `x-api-key` matching the `INTERNAL_API_KEY` defined in the agent's `.env` file.

*(Note: The system also has a `/health` endpoint for readiness/liveness checks, but `/assess` is the primary operational endpoint).*

---

## 2. Request Data: What to Send (The `BreachPayload`)

When a disaster threshold is crossed, the main backend must send a JSON payload containing the physical metrics, location data, and database hints.

### JSON Request Schema
```json
{
  "breach_id": "123e4567-e89b-12d3-a456-426614174000",
  "disaster_kind": "flood", 
  "location_name": "Sukkur",
  "district": "sukkur",
  "province": "sindh",
  "latitude": 27.7052,
  "longitude": 68.8574,
  "observed_value": 105.3,
  "threshold_value": 100.0,
  "breach_severity": "emergency",
  "metric_name": "gauge_pct_of_danger",
  "observation_time": "2025-07-15T14:30:00+05:00",
  "source_api": "google_flood_hub",
  "is_forecast_breach": false,
  "forecast_horizon_h": null,
  "gauge_id": "optional-uuid-here",
  "usgs_event_id": null,
  "weather_location_id": null
}
```

### Parameter Explanations (What to pass to the Agent)
* **`breach_id`**: Your internal unique identifier for this alert.
* **`disaster_kind`**: The type of disaster (e.g., `earthquake`, `flood`, `heatwave`, `cyclone`, `drought`).
* **`location_name`, `district`, `province`**: Text definitions of where the disaster is happening. **Crucial:** The `district` must match a district in the agent's database for accurate data lookups.
* **`latitude` & `longitude`**: The exact coordinates. Used by the agent to find infrastructure (hospitals, dams) within the impact radius.
* **`observed_value` & `threshold_value`**: The data that caused the alarm (e.g., water level hit 105.3, but the danger line is 100.0).
* **`breach_severity`**: Categorization of the breach (`watch`, `warning`, `emergency`, `extreme`).
* **`observation_time`**: ISO-8601 timestamp of when the event was recorded.
* **Database Hints (`gauge_id`, `usgs_event_id`, `weather_location_id`)**: These are highly recommended. They allow the agent to directly query the database for real-time historical data regarding this specific event instead of guessing.

---

## 3. How to Call the API from the Main Backend

You can call this API using standard HTTP libraries. Below are examples using `cURL` and Python (`httpx` / `requests`).

### Python Example (`httpx` or `requests`)
```python
import requests

url = "http://localhost:8001/api/v1/assess"
headers = {
    "x-api-key": "YOUR_INTERNAL_API_KEY",  # Must presennt .env file name is RISK_ANALYSIS_API_KEY and in risk folder match the Agent's .env file
    "Content-Type": "application/json"
}
payload = {
    "breach_id": "abcd-1234",
    "disaster_kind": "flood",
    "location_name": "Nowshera",
    "district": "nowshera",
    "province": "khyber_pakhtunkhwa",
    "latitude": 34.0158,
    "longitude": 71.9812,
    "observed_value": 150000.0,
    "threshold_value": 100000.0,
    "breach_severity": "warning",
    "metric_name": "river_discharge_cusecs",
    "observation_time": "2025-08-10T09:00:00Z",
    "source_api": "google_flood_hub"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json()) # This will be the RiskAssessmentReport
```

---

## 4. Complete Working Mechanism (What happens internally?)

1. **API Receives Payload**: The `/assess` endpoint validates the incoming JSON against the `BreachPayload` model. It checks the API key for authorization.
2. **Contextualization**: The API creates an `assessment_id` and formats a massive text prompt combining the input data (Location, Disaster Type, Severity).
3. **Agent Activation**: The system wakes up the OpenAI Agent (`gpt-4.1-mini`). 
4. **Tool Usage**: Based on the disaster, the agent uses its assigned python functions (Tools):
   - It calls `get_location_data(district, province)` to get population, terrain, and demographics.
   - It calls `get_infrastructure_at_risk(lat, lon)` to find nearby hospitals, dams, and bridges.
   - It calls `get_current_disaster_data(...)` to pull time-series data on the flood or earthquake.
5. **Scoring**: The agent applies domain-specific logic to calculate 5 core scores: Hazard Severity, Exposure, Vulnerability, Escalation Risk, and Response Capacity.
6. **Output Generation**: The agent formats its findings into the strict JSON schema defined by `RiskAssessmentReport`.
7. **Response**: The API returns this massive JSON object back to your main backend.

---

## 5. Expected Output: The `RiskAssessmentReport`

The agent does not return a chat message. It returns a massive, strictly typed JSON object containing exactly what the "Precaution Definer Agent" needs to save lives.

### Example Output Structure
```json
{
  "assessment_id": "uuid-of-this-specific-report",
  "breach_id": "abcd-1234",
  "disaster_kind": "flood",
  "risk_level": "EXTREME",
  "composite_risk_score": 185.5,
  
  "terrain_assessment": {
    "terrain_type": "mountainous",
    "terrain_vulnerability_score": 180,
    "terrain_multiplier": 1.2
  },
  
  "hazard_severity": {
    "score": 190.0,
    "justification": "Water levels exceed historical maximums by 5%."
  },
  
  "exposure": {
    "score": 150.0,
    "population_breakdown": {
      "total_population": 250000,
      "estimated_directly_affected": 45000
    },
    "infrastructure_at_risk": {
      "hospitals_count": 3,
      "critical_bridges": ["Nowshera Main Bridge"]
    }
  },
  
  "vulnerability": {
    "score": 140.0,
    "building_stock_type": "mostly_kutcha"
  },
  
  "escalation_risk": {
    "is_worsening": true,
    "secondary_disasters_possible": ["waterborne_disease", "landslides"]
  },
  
  "response_capacity": {
    "score": 40.0,
    "medical_capacity_score": 30.0,
    "response_time_estimate_hours": 12.5
  },
  
  "impact_estimates": {
    "estimated_economic_damage_usd": "$15M - $25M",
    "death_risk_level": "HIGH"
  },
  
  "recommended_response_urgency": "EMERGENCY",
  "critical_actions_needed": [
    "Immediate evacuation of low-lying riverbank areas.",
    "Mobilize military engineering corps to secure Nowshera Main Bridge."
  ]
}
```

### Key Takeaways of the Output:
- **`risk_level`** and **`composite_risk_score`**: The absolute final verdict of how bad the situation is.
- **Nested Scores**: Detailed mathematical breakdowns of *why* the risk is what it is (Hazard, Exposure, Vulnerability).
- **`critical_actions_needed`**: A list of immediate actions that your main backend or "Precaution Agent" can use to generate alerts for users on the ground.
