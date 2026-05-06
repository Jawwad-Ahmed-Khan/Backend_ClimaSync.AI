"""
ClimaSync.AI - Agent Pipeline Demo Script

Usage (after backend is running with DB connected):
    cd d:/fyp/Backend_ClimaSync.AI
    uv run python test_agents_demo.py           # Agent 1 only (no OpenAI cost)
    uv run python test_agents_demo.py --full    # Full 4-agent pipeline
    uv run python test_agents_demo.py --mock    # Mock output (no DB needed)

Requirements:
    - Backend running on http://localhost:8001
    - Supabase project unpaused (ncceiwuskeergtfauojc)
    - OPENAI_API_KEY set in .env (for --full only)
    - At least one disaster event in the disaster_events table
"""

import asyncio
import json
import sys
import httpx

BASE_URL = "http://localhost:8001/api/v1"


async def login(client: httpx.AsyncClient) -> str:
    """Get a JWT token for auth-protected endpoints."""
    # Try login — replace with real credentials if needed
    resp = await client.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@climasync.ai",
        "password": "Admin1234!"
    })
    if resp.status_code != 200:
        print(f"⚠️  Login failed ({resp.status_code}) — trying without auth for public endpoints")
        return ""
    token = resp.json().get("access_token", "")
    print(f"✅ Logged in — token: {token[:30]}...")
    return token


async def get_disaster_events(client: httpx.AsyncClient) -> list[dict]:
    """Fetch active disaster events (now public endpoint)."""
    try:
        resp = await client.get(f"{BASE_URL}/disasters?limit=5&offset=0")
    except (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError) as e:
        print(f"\n❌ DB connection error: {type(e).__name__}")
        print("   The backend is running but cannot reach Supabase.")
        print("   → Go to https://supabase.com/dashboard and restore project: ncceiwuskeergtfauojc")
        print("   → Then retry: uv run python test_agents_demo.py")
        print("   → Or run mock demo: uv run python test_agents_demo.py --mock")
        return []
    if resp.status_code != 200:
        print(f"❌ GET /disasters failed: {resp.status_code} — {resp.text[:200]}")
        return []
    events = resp.json()
    print(f"\n📋 Found {len(events)} disaster events:")
    for e in events:
        print(f"   [{e.get('event_id', '?')[:8]}...] {e.get('title', 'Unknown')} — {e.get('event_type', '?')} ({e.get('status', '?')})")
    return events


async def run_full_pipeline(client: httpx.AsyncClient, event_id: str, token: str) -> None:
    """Trigger the full 4-agent pipeline for a disaster event."""
    print(f"\n🚀 Running full agent pipeline for event: {event_id}")
    print("   Agent 1 → Data Extraction (no LLM)")
    print("   Agent 2 → Risk Analysis (GPT-4o-mini)")
    print("   Agent 3 → Task Definer (GPT-4o-mini)")
    print("   Agent 4 → Task Allocator (GPT-4o-mini)")
    print("   (This may take 30–60 seconds...)\n")

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = await client.post(
        f"{BASE_URL}/agents/analyze/{event_id}",
        headers=headers,
        timeout=120.0,
    )

    if resp.status_code != 200:
        print(f"❌ Pipeline failed: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        return

    result = resp.json()
    print("=" * 60)
    print("✅ AGENT PIPELINE COMPLETE")
    print("=" * 60)

    risk = result["risk_report"]
    print(f"\n📊 RISK REPORT")
    print(f"   Risk Level:    {risk['risk_level'].upper()}")
    print(f"   Severity:      {risk['severity_score']}/10")
    print(f"   Confidence:    {risk['confidence']*100:.0f}%")
    print(f"   Population:    ~{risk['affected_population_estimate']:,} affected")
    print(f"   Response Win:  {risk['recommended_response_window_hours']}h")
    print(f"   Key Factors:   {', '.join(risk['key_risk_factors'][:3])}")
    print(f"\n   Reasoning: {risk['reasoning'][:200]}...")

    print(f"\n📌 TASKS")
    print(f"   Created:   {result['tasks_created']}")
    print(f"   Allocated: {result['tasks_allocated']} (assigned to NGOs)")
    print(f"   Pending:   {len(result['unallocated_task_ids'])} unallocated")
    print(f"\n   Summary: {result['allocation_summary'][:200]}")


async def run_debug_extract(client: httpx.AsyncClient, event_id: str, token: str) -> None:
    """Run only Agent 1 — Data Extraction (no LLM, fast)."""
    print(f"\n🔍 Running Agent 1 only (Data Extraction) for: {event_id}")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = await client.post(
        f"{BASE_URL}/agents/extract/{event_id}",
        headers=headers,
        timeout=30.0,
    )
    if resp.status_code != 200:
        print(f"❌ Extract failed: {resp.status_code} — {resp.text[:300]}")
        return

    ctx = resp.json()
    print("\n✅ DISASTER CONTEXT (Agent 1 output):")
    print(f"   Event:    {ctx.get('title')}")
    print(f"   Type:     {ctx.get('event_type')}")
    print(f"   Location: {ctx.get('location_name')} ({ctx.get('district')}, {ctx.get('province')})")
    print(f"   Coords:   {ctx.get('latitude')}, {ctx.get('longitude')}")
    print(f"   NGOs:     {len(ctx.get('nearby_ngos', []))} verified NGOs in range")
    weather = ctx.get('weather_summary', {})
    if 'temperature_2m' in weather:
        print(f"   Weather:  {weather.get('temperature_2m')}°C, {weather.get('precipitation_probability_max')}% rain")
    sensor = ctx.get('sensor_readings', {})
    print(f"   Sensors:  {json.dumps(sensor)[:100]}")


def mock_demo() -> None:
    """Print realistic expected output to show what the pipeline produces."""
    print("\n" + "=" * 60)
    print("  MOCK MODE — Expected Agent Pipeline Output")
    print("  (Run without --mock once Supabase is unpaused)")
    print("=" * 60)

    print("""
✅ Backend health: {'status': 'healthy', 'version': '0.1.0'}

📋 Found 3 disaster events:
   [a1b2c3d4...] Flash Flood in Swat Valley — flood (active)
   [e5f6g7h8...] Earthquake near Quetta — earthquake (monitoring)
   [i9j0k1l2...] Cyclone Warning Karachi Coast — cyclone (active)

▶  Using event: a1b2c3d4-...-swat-flood

🔍 Running Agent 1 only (Data Extraction) for: a1b2c3d4-...

✅ DISASTER CONTEXT (Agent 1 output):
   Event:    Flash Flood in Swat Valley
   Type:     flood
   Location: Swat Valley (Swat, Khyber Pakhtunkhwa)
   Coords:   35.2227, 72.4258
   NGOs:     4 verified NGOs in range
   Weather:  28.3°C, 85% rain probability
   Sensors:  {"gauge_level_m": 4.2, "threshold_m": 3.0, "breached": true}
""")

    print("--- If run with --full (3 GPT-4o-mini calls) ---")
    print("""
🚀 Running full agent pipeline...

============================================================
✅ AGENT PIPELINE COMPLETE
============================================================

📊 RISK REPORT (Agent 2 — Risk Analysis)
   Risk Level:    HIGH
   Severity:      7.8/10
   Confidence:    89%
   Population:    ~52,000 affected
   Response Win:  8h
   Key Factors:   flash flooding, dense population, limited road access

   Reasoning: The Swat Valley event presents HIGH risk. Current gauge
   levels (4.2m) exceed the 3.0m threshold. Weather forecast shows
   sustained heavy rainfall (85% probability) over next 12 hours...

📌 TASKS (Agent 3 — Task Definer + Agent 4 — Task Allocator)
   Created:   6
   Allocated: 5  (assigned to NGOs)
   Pending:   1  (no NGO with boats available)

   Summary: 5 of 6 tasks assigned to 3 NGOs — Al-Khidmat Foundation
   (medical + food), Rescue 1122 (evacuation), Edhi Foundation (shelter).
   Task 'river rescue boat deployment' unallocated — no verified NGO
   with rescue_boats > 0 within 50km radius.
""")
    print("=" * 60)
    print("Mock demo complete. Restore Supabase to run live.")
    print("=" * 60)

async def main():
    if "--mock" in sys.argv:
        mock_demo()
        return

    print("=" * 60)
    print("  ClimaSync.AI - Agent Pipeline Demo")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        try:
            resp = await client.get("http://localhost:8001/health")
            print(f"\n✅ Backend health: {resp.json()}")
        except Exception as e:
            print(f"❌ Backend not reachable: {e}")
            sys.exit(1)

        # 2. Get auth token
        token = await login(client)

        # 3. List disaster events
        events = await get_disaster_events(client)
        if not events:
            return

        # 4. Pick first event
        event_id = events[0]["event_id"]
        print(f"\n▶  Using event: {event_id}")

        # Choose demo mode
        if "--full" in sys.argv:
            await run_full_pipeline(client, event_id, token)
        else:
            print("\n💡 Running Agent 1 only (safe, no OpenAI cost)")
            print("   Pass --full to run all 4 agents (uses ~3 GPT-4o-mini calls)")
            await run_debug_extract(client, event_id, token)

        print("\n" + "=" * 60)
        print("Demo complete! Check http://localhost:8001/docs for all endpoints.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
