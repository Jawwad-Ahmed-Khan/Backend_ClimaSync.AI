import httpx
import uuid
import json
import asyncio
from datetime import datetime, timezone

# --- CONFIGURATION ---
BACKEND_URL = "http://localhost:8000/api/v1/alerts/incoming"
# Ensure this matches your .env 'INCOMING_ALERT_API_KEY'
API_KEY = "" 

async def send_alert(name, payload):
    """Utility to send a single alert and print result."""
    print(f"\n🚀 Dispatching {name} alert...")
    print(f"📦 Breach ID: {payload['breach_id']}")

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                BACKEND_URL,
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code in (200, 201):
                print(f"✅ SUCCESS: {name} alert accepted.")
            elif response.status_code == 409:
                print(f"⚠️ CONFLICT: {payload['breach_id']} already exists.")
            elif response.status_code == 422:
                print(f"❌ VALIDATION ERROR: {response.text}")
            else:
                print(f"❌ FAILED: HTTP {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

async def run_full_suite():
    """Triggers all three disaster types."""
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. EARTHQUAKE (USGS)
    earthquake = {
        "breach_id": str(uuid.uuid4()),
        "source_api": "usgs",
        "disaster_kind": "earthquake",
        "location_name": "Quetta, Balochistan",
        "district": "quetta",
        "province": "balochistan",
        "latitude": 30.1798,
        "longitude": 66.9750,
        "metric_name": "magnitude",
        "observed_value": 6.8,
        "threshold_value": 5.0,
        "unit": "richter",
        "breach_severity": "emergency",
        "observation_time": now_iso,
        "detected_at": now_iso,
        "is_forecast": False,
        "seismic_event_id": f"us_{uuid.uuid4().hex[:6]}"
    }

    # 2. FLOOD (Google Flood Hub)
    flood = {
        "breach_id": str(uuid.uuid4()),
        "source_api": "google_flood_hub",
        "disaster_kind": "flood",
        "location_name": "Nowshera, KP",
        "district": "nowshera",
        "province": "khyber_pakhtunkhwa",
        "latitude": 34.0150,
        "longitude": 71.9747,
        "metric_name": "water_level",
        "observed_value": 14.2,
        "threshold_value": 10.0,
        "unit": "meters",
        "breach_severity": "extreme",
        "observation_time": now_iso,
        "detected_at": now_iso,
        "is_forecast": False,
        "gauge_id": f"gauge_{uuid.uuid4().hex[:6]}"
    }

    # 3. WEATHER / HEAVY RAIN (Open-Meteo)
    weather = {
        "breach_id": str(uuid.uuid4()),
        "source_api": "open_meteo",
        "disaster_kind": "heavy_rain",
        "location_name": "Lahore, Punjab",
        "district": "lahore",
        "province": "punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "metric_name": "precipitation",
        "observed_value": 120.0,
        "threshold_value": 50.0,
        "unit": "mm",
        "breach_severity": "warning",
        "observation_time": now_iso,
        "detected_at": now_iso,
        "is_forecast": True,
        "forecast_horizon_h": 24,
        "weather_location_id": f"loc_{uuid.uuid4().hex[:6]}"
    }

    # Execute all
    await send_alert("EARTHQUAKE", earthquake)
    await send_alert("FLOOD", flood)
    await send_alert("WEATHER", weather)

    print("\n--- TEST COMPLETE ---")
    print("Check your dashboard WebSockets for 3 incoming alerts.")

if __name__ == "__main__":
    asyncio.run(run_full_suite())
