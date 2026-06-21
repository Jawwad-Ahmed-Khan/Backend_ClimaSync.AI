import asyncio
import httpx
import json
import uuid

# --- CONFIGURATION ---
MAIN_BACKEND_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "super_admin@climasync.ai"
ADMIN_PASSWORD = "password123" # Adjust if known otherwise

async def test_end_to_end_risk():
    print("🚀 Starting End-to-End Risk Analysis Proxy Test...")
    
    async with httpx.AsyncClient(timeout=310.0) as client:
        # 1. Login to get token
        print(f"Step 1: Logging in as {ADMIN_EMAIL}...")
        try:
            login_resp = await client.post(f"{MAIN_BACKEND_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if login_resp.status_code != 200:
                print(f"❌ Login FAILED: {login_resp.status_code} - {login_resp.text}")
                print("💡 Tip: If you don't know the password, check your 'seed_admin_data.py' or .env")
                return
            
            token = login_resp.json().get("access_token")
            print("✅ Login SUCCESS. Token retrieved.")
        except Exception as e:
            print(f"❌ Connection Error during login: {e}")
            return

        # 2. Call the Main Backend Proxy
        print("\nStep 2: Calling Main Backend Proxy (POST /risk-analysis/assess)...")
        payload = {
            "breach_id": str(uuid.uuid4()), # Unique for persistence test
            "disaster_kind": "flood",
            "location_name": "Sukkur Barrage",
            "district": "Sukkur",
            "province": "sindh",
            "latitude": 27.712,
            "longitude": 68.852,
            "observed_value": 125.5,
            "threshold_value": 100.0,
            "breach_severity": "emergency",
            "metric_name": "gauge_pct_of_danger",
            "observation_time": "2026-05-13T10:00:00Z",
            "source_api": "google_flood_hub",
            "is_forecast_breach": False,
            "gauge_id": "G-SUKKUR-001"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        print("📡 Forwarding request through Main Backend (Waiting for AI Reasoning)...")
        try:
            response = await client.post(
                f"{MAIN_BACKEND_URL}/risk-analysis/assess",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print("\n🎉 SUCCESS! Full Risk Assessment Report Received via Main Backend.")
                print(f"   Assessment ID: {data.get('assessment_id')}")
                print(f"   Risk Level: {data.get('risk_level')}")
                print(f"   Composite Score: {data.get('composite_risk_score')}")
                print(f"   Persistence: The report has been saved to 'risk_analyses' table.")
                print("\n--- Summary of Justification ---")
                print(data.get('risk_level_justification'))
            else:
                print(f"\n❌ PROXY FAILED: HTTP {response.status_code}")
                print(f"   Detail: {response.text}")

        except Exception as e:
            print(f"\n❌ ERROR during proxy call: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_end_to_end_risk())
