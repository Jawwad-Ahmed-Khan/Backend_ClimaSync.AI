import asyncio
import httpx
import json

async def test_frontend_to_backend():
    url = "http://127.0.0.1:8000/api/v1/risk-analysis/assess"
    
    # Using the JWT token the user provided in the network trace
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNzliYzI0Ni01NGM4LTQ4ODMtOTBiNi0yOWVkYzg3MWE0MWEiLCJleHAiOjE3Nzg2NjEwMDEsImlhdCI6MTc3ODY1OTIwMSwidHlwZSI6ImFjY2VzcyIsInJvbGUiOiJhZG1pbiJ9.jPg9F9hzi9u-EkT77UwZWGNKdmF8Qi4B4sVznWKLkBI"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "breach_id": "a402242f-4568-4642-be8f-50bfb65340a7",
        "disaster_kind": "flood",
        "location_name": "Larkana",
        "district": "Swat",
        "province": "khyber_pakhtunkhwa",
        "latitude": 27.5589,
        "longitude": 68.212,
        "observed_value": 5.0,
        "threshold_value": 4.0,
        "breach_severity": "warning",
        "metric_name": "water_level_meters",
        "observation_time": "2026-05-13T08:13:39.457Z",
        "source_api": "usgs",
        "is_forecast_breach": False,
        "forecast_horizon_h": None,
        "gauge_id": None,
        "usgs_event_id": None,
        "weather_location_id": None
    }

    print(f"Sending request to Main Backend ({url})...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! The end-to-end flow is working.")
                data = response.json()
                print(f"Assessment ID: {data.get('assessment_id')}")
                print(f"Risk Level: {data.get('risk_level')}")
                print(f"Actions Needed: {data.get('critical_actions_needed')}")
            else:
                print("❌ FAILED. Response body:")
                try:
                    print(json.dumps(response.json(), indent=2))
                except:
                    print(response.text)
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_frontend_to_backend())
