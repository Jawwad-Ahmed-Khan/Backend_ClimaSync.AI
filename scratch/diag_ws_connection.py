import asyncio
import websockets
import json
import httpx

# --- SETTINGS ---
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/alerts"
# Test credentials (adjust if you have a real admin user)
EMAIL = "admin@climasync.ai"
PASSWORD = "password123"

async def diagnose_ws():
    print(f"🔍 Starting WebSocket Diagnosis...")
    
    # 1. Get an Admin Token
    print(f"Step 1: Authenticating as Admin...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
                "email": EMAIL,
                "password": PASSWORD
            })
            if resp.status_code != 200:
                print(f"❌ Failed to login: {resp.status_code} - {resp.text}")
                return
            
            token = resp.json().get("access_token")
            print(f"✅ Login successful. Token retrieved.")
    except Exception as e:
        print(f"❌ Connection error during login: {e}")
        return

    # 2. Attempt WebSocket Connection
    full_ws_url = f"{WS_URL}?token={token}"
    print(f"Step 2: Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(full_ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # 3. Trigger a synthetic alert to see if this client receives it
            print("Step 3: Triggering synthetic alert via REST API...")
            async with httpx.AsyncClient() as client:
                alert_payload = {
                    "breach_id": "test-ws-diag-123",
                    "source_api": "usgs",
                    "disaster_kind": "earthquake",
                    "latitude": 30.0,
                    "longitude": 67.0,
                    "metric_name": "magnitude",
                    "observed_value": 8.0,
                    "threshold_value": 5.0,
                    "unit": "richter",
                    "breach_severity": "extreme",
                    "observation_time": "2026-05-13T12:00:00Z",
                    "detected_at": "2026-05-13T12:05:00Z"
                }
                headers = {"X-API-Key": ""} # Default empty if not set
                await client.post(f"{BASE_URL}/api/v1/alerts/incoming", json=alert_payload, headers=headers)
            
            # 4. Wait for message
            print("Step 4: Waiting for broadcast message...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"🎉 SUCCESS! Received broadcast: {json.dumps(data, indent=2)}")
            except asyncio.TimeoutError:
                print("❌ TIMEOUT: Connected but did not receive the broadcast.")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket closed unexpectedly: {e.code} - {e.reason}")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_ws())
