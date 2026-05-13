# Deployment and Testing Guide
## Complete Setup Instructions for ClimaSync.AI Disaster Management Workflow

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Backend Setup](#backend-setup)
3. [Frontend Setup](#frontend-setup)
4. [Agent Configuration](#agent-configuration)
5. [Testing Workflow](#testing-workflow)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Python 3.10+ (for backend)
- Node.js 18+ (for frontend)
- PostgreSQL 14+ (database)
- Git

### Environment Setup
```bash
# Check versions
python --version
node --version
psql --version
```

---

## Backend Setup

### Step 1: Navigate to Backend Directory
```bash
cd F:\ClimasyncAI_backend
```

### Step 2: Install Dependencies
```bash
# If using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Edit `.env.local`:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/climasync_db

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Agent Microservices
RISK_ANALYSIS_AGENT_URL=http://localhost:8002
PRECAUTIONARY_AGENT_URL=http://localhost:8003
AGENT_API_KEY=climasync-agent-secure-key-2026

# CORS
FRONTEND_URL=http://localhost:3000
```

### Step 4: Create Database Tables
```bash
# Run migrations
alembic upgrade head
```

### Step 5: Create Admin Workflow Module
```bash
# Create module directory
mkdir -p app/modules/admin_workflow

# Create files (copy code from BACKEND_IMPLEMENTATION_CODE.md)
touch app/modules/admin_workflow/__init__.py
touch app/modules/admin_workflow/models.py
touch app/modules/admin_workflow/schemas.py
touch app/modules/admin_workflow/services.py
touch app/modules/admin_workflow/routes.py
touch app/modules/admin_workflow/agent_client.py
```

Copy the code from `BACKEND_IMPLEMENTATION_CODE.md` and `BACKEND_SERVICES_ROUTES.md` into respective files.

### Step 6: Register Routes in Main App
Edit `main.py` or `app/main.py`:
```python
from app.modules.admin_workflow.routes import router as admin_workflow_router

# Add this line after other router registrations
app.include_router(
    admin_workflow_router,
    prefix="/api",
    tags=["Admin Workflow"]
)
```

### Step 7: Start Backend Server
```bash
# Development mode
uvicorn main:app --reload --port 8000

# Or if main.py is in app folder
uvicorn app.main:app --reload --port 8000
```

Backend should now be running at `http://localhost:8000`

---

## Frontend Setup

### Step 1: Navigate to Frontend Directory
```bash
cd F:\ClimaSyncAI_frontend
```

### Step 2: Install Dependencies
```bash
npm install
# or
yarn install
```

### Step 3: Configure Environment Variables
Edit `.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Step 4: Fix API Client Import
Update `app/_lib/admin/adminAuthService.ts`:
```typescript
// Change this line:
import { apiClient } from '../api/apiClient';

// To this:
import { apiClient } from '../apiClient';
```

Update all other service files similarly:
- `app/_lib/admin/thresholdAlertService.ts`
- `app/_lib/admin/riskAnalysisService.ts`
- `app/_lib/admin/precautionaryService.ts`

### Step 5: Start Frontend Server
```bash
npm run dev
# or
yarn dev
```

Frontend should now be running at `http://localhost:3000`

---

## Agent Configuration

### Risk Analysis Agent Setup

**Location:** `F:\ClimasyncAI_Agents\Risk_Analysis`

1. Create API endpoint in the agent:

**File:** `app/api/routes.py` (or similar)
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter()

class RiskAnalysisRequest(BaseModel):
    alert_id: str
    location: Dict[str, Any]
    sensor_data: Dict[str, Any]
    historical_data: Dict[str, Any]

class RiskAnalysisResponse(BaseModel):
    risk_score: int
    risk_level: str
    disaster_type: str
    affected_area_km2: float
    estimated_population_affected: int
    confidence_score: int
    analysis_summary: str
    detailed_analysis: Dict[str, Any]
    recommended_actions: List[str]

@router.post("/api/analyze", response_model=RiskAnalysisResponse)
async def analyze_risk(request: RiskAnalysisRequest):
    """
    Analyze risk based on threshold breach data
    """
    # Your existing risk analysis logic here
    # This is a dummy response for testing
    return RiskAnalysisResponse(
        risk_score=85,
        risk_level="HIGH",
        disaster_type="FLOOD",
        affected_area_km2=250.5,
        estimated_population_affected=50000,
        confidence_score=92,
        analysis_summary="High risk of urban flooding in the area due to excessive rainfall exceeding threshold by 50%.",
        detailed_analysis={
            "severity_factors": [
                "Rainfall 50% above threshold",
                "Poor drainage infrastructure",
                "High population density"
            ],
            "vulnerability_assessment": "Urban area with limited flood defenses and high population density.",
            "historical_comparison": "Similar event in 2020 affected 45,000 people.",
            "prediction_model_output": {}
        },
        recommended_actions=[
            "Evacuate low-lying areas immediately",
            "Deploy emergency response teams",
            "Activate flood warning systems",
            "Set up temporary shelters"
        ]
    )
```

2. Start the agent:
```bash
cd F:\ClimasyncAI_Agents\Risk_Analysis
uvicorn main:app --reload --port 8002
```

### Precautionary Agent Setup

**Location:** `F:\ClimaSyncAI_dataCollection_Microservice` (or create new folder)

1. Create API endpoint:

**File:** `app/api/routes.py`
```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid

router = APIRouter()

class PrecautionaryRequest(BaseModel):
    analysis_id: str
    risk_analysis_data: Dict[str, Any]
    location: Dict[str, Any]

class RequiredResources(BaseModel):
    personnel: int
    vehicles: int
    supplies: List[str]

class PrecautionaryMeasure(BaseModel):
    measure_id: str
    category: str
    priority: str
    title: str
    description: str
    target_population: int
    estimated_duration_hours: int
    required_resources: RequiredResources
    implementation_steps: List[str]

class Timeline(BaseModel):
    immediate_actions: List[str]
    short_term_actions: List[str]
    long_term_actions: List[str]

class PrecautionaryResponse(BaseModel):
    overall_strategy: str
    measures: List[PrecautionaryMeasure]
    timeline: Timeline
    estimated_cost: float

@router.post("/api/generate-measures", response_model=PrecautionaryResponse)
async def generate_measures(request: PrecautionaryRequest):
    """
    Generate precautionary measures based on risk analysis
    """
    # Your existing precautionary measures generation logic here
    # This is a dummy response for testing
    return PrecautionaryResponse(
        overall_strategy="Multi-phase response focusing on immediate evacuation, followed by shelter setup and long-term infrastructure improvements.",
        measures=[
            PrecautionaryMeasure(
                measure_id=str(uuid.uuid4()),
                category="EVACUATION",
                priority="IMMEDIATE",
                title="Evacuate Low-Lying Areas",
                description="Immediate evacuation of residents in flood-prone zones to higher ground and designated safe areas.",
                target_population=15000,
                estimated_duration_hours=6,
                required_resources=RequiredResources(
                    personnel=200,
                    vehicles=50,
                    supplies=["Emergency kits", "Medical supplies", "Food packets", "Water bottles"]
                ),
                implementation_steps=[
                    "Activate emergency alert system",
                    "Deploy evacuation teams to affected areas",
                    "Set up temporary shelters in safe zones",
                    "Coordinate with local authorities"
                ]
            ),
            PrecautionaryMeasure(
                measure_id=str(uuid.uuid4()),
                category="SHELTER",
                priority="HIGH",
                title="Establish Emergency Shelters",
                description="Set up temporary shelters with basic amenities for evacuated population.",
                target_population=15000,
                estimated_duration_hours=12,
                required_resources=RequiredResources(
                    personnel=100,
                    vehicles=20,
                    supplies=["Tents", "Blankets", "Cooking equipment", "Sanitation facilities"]
                ),
                implementation_steps=[
                    "Identify suitable shelter locations",
                    "Deploy shelter infrastructure",
                    "Organize food and water distribution",
                    "Set up medical aid stations"
                ]
            ),
            PrecautionaryMeasure(
                measure_id=str(uuid.uuid4()),
                category="MEDICAL",
                priority="HIGH",
                title="Deploy Medical Teams",
                description="Deploy medical teams to provide emergency healthcare and prevent disease outbreaks.",
                target_population=50000,
                estimated_duration_hours=24,
                required_resources=RequiredResources(
                    personnel=50,
                    vehicles=10,
                    supplies=["Medical kits", "Medicines", "Ambulances", "First aid supplies"]
                ),
                implementation_steps=[
                    "Set up mobile medical units",
                    "Conduct health screenings",
                    "Distribute preventive medicines",
                    "Monitor for waterborne diseases"
                ]
            )
        ],
        timeline=Timeline(
            immediate_actions=[
                "Activate emergency alert system",
                "Deploy evacuation teams",
                "Set up command center"
            ],
            short_term_actions=[
                "Establish temporary shelters",
                "Distribute relief supplies",
                "Conduct damage assessment"
            ],
            long_term_actions=[
                "Infrastructure repair and improvement",
                "Flood prevention measures",
                "Community resilience training"
            ]
        ),
        estimated_cost=5000000.00
    )
```

2. Start the agent:
```bash
cd F:\ClimaSyncAI_dataCollection_Microservice
uvicorn main:app --reload --port 8003
```

---

## Testing Workflow

### Test 1: Create Admin Account

1. Open browser and navigate to: `http://localhost:3000/admin/create-account`
2. Fill in the form:
   - Full Name: John Doe
   - Email: admin@climasync.ai
   - Organization: NDMA Pakistan
   - Password: SecurePass123!
   - Confirm Password: SecurePass123!
3. Click "Create Admin Account"
4. You should be redirected to `/admin` dashboard

### Test 2: Simulate Data Collector Agent Alert

Use cURL or Postman:

```bash
curl -X POST http://localhost:8000/api/admin/threshold-alerts \
  -H "Authorization: Bearer climasync-agent-secure-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "rainfall",
    "location": {
      "latitude": 24.8607,
      "longitude": 67.0011,
      "location_name": "Karachi",
      "province": "Sindh"
    },
    "current_value": 150.5,
    "threshold_value": 100.0,
    "breach_percentage": 50.5,
    "severity": "HIGH",
    "data_source": "PMD Weather Station KHI-001"
  }'
```

Expected Response:
```json
{
  "alert_id": "uuid",
  "status": "NEW",
  "created_at": "2026-05-11T10:30:00Z"
}
```

### Test 3: View Alerts in Admin Panel

1. Navigate to: `http://localhost:3000/admin/threshold-alerts`
2. You should see the alert created in Test 2
3. Click "Analyze Risk" button

### Test 4: Complete Workflow

1. **View Alert**: Alert appears in threshold alerts page
2. **Request Risk Analysis**: Click "Analyze Risk"
   - Backend sends request to Risk Analysis Agent (port 8002)
   - Frontend polls for result
   - Risk analysis modal appears with results
3. **Generate Precautions**: Click "Generate Precautions"
   - Backend sends request to Precautionary Agent (port 8003)
   - Frontend polls for result
   - Precautionary measures modal appears with detailed measures
4. **Complete**: Click "Close & Complete"

### Test 5: Verify Database

```sql
-- Check admin users
SELECT * FROM admin_users;

-- Check threshold alerts
SELECT * FROM threshold_breach_alerts;

-- Check risk analyses
SELECT * FROM risk_analyses;

-- Check precautionary measures
SELECT * FROM precautionary_measures;
```

---

## Troubleshooting

### Issue: Backend won't start

**Solution:**
```bash
# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Kill the process if needed
taskkill /PID <process_id> /F

# Restart backend
uvicorn main:app --reload --port 8000
```

### Issue: Frontend API calls fail

**Solution:**
1. Check `.env.local` has correct API URL
2. Verify backend is running on port 8000
3. Check browser console for CORS errors
4. Ensure CORS is configured in backend:

```python
# In main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Agent communication fails

**Solution:**
1. Verify agents are running:
   - Risk Analysis Agent: `http://localhost:8002`
   - Precautionary Agent: `http://localhost:8003`
2. Test agent endpoints directly:
```bash
curl http://localhost:8002/docs
curl http://localhost:8003/docs
```
3. Check agent URLs in backend `.env.local`

### Issue: Database connection error

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready

# Verify database exists
psql -U postgres -c "\l"

# Create database if needed
createdb climasync_db

# Run migrations
alembic upgrade head
```

### Issue: Authentication fails

**Solution:**
1. Check JWT secret key is set in `.env.local`
2. Verify token is being sent in Authorization header
3. Check token expiration settings
4. Clear browser localStorage and login again

---

## Production Deployment Checklist

- [ ] Change all default passwords and API keys
- [ ] Use environment-specific `.env` files
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure production database with backups
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Enable database connection pooling
- [ ] Set up CI/CD pipeline
- [ ] Configure reverse proxy (Nginx/Apache)
- [ ] Enable security headers
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Configure auto-scaling for agents
- [ ] Set up database migrations strategy
- [ ] Enable API documentation (Swagger/ReDoc)
- [ ] Configure backup and disaster recovery

---

## Next Steps

1. ✅ Backend API implementation complete
2. ✅ Frontend services and UI complete
3. ✅ Admin account creation page complete
4. ⏳ Test complete workflow with dummy data
5. ⏳ Integrate with real agent microservices
6. ⏳ Deploy to staging environment
7. ⏳ Conduct end-to-end testing
8. ⏳ Deploy to production

---

**Congratulations!** Your disaster management workflow is now fully implemented and ready for testing.
