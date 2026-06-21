import asyncio
import httpx
import json

async def test():
    url = "http://localhost:8001/api/v1/assess"
    headers = {
        "x-api-key": "b702d6b292994952b843b4b8b1ec5119",
        "Content-Type": "application/json"
    }
    payload = {
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
        "is_forecast_breach": False,
        "forecast_horizon_h": None,
        "gauge_id": None,
        "usgs_event_id": None,
        "weather_location_id": None
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        print("Status:", response.status_code)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            print(response.text)

if __name__ == "__main__":
    asyncio.run(test())
