# Backend Implementation Prompt for ClimaSync.AI Disaster Management Workflow

## Context
I need you to implement a complete disaster management workflow backend for ClimaSync.AI. The frontend is already complete and waiting for these backend APIs. This workflow integrates with three microservices: Data Collector Agent, Risk Analysis Agent, and Precautionary Agent.

## Project Information
- **Backend Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT Bearer Tokens
- **Location**: `F:\ClimasyncAI_backend`
- **Existing Structure**: `app/modules/` contains auth, admin, disasters, ngo, notifications, resources, social, tasks, users

## What to Implement

### 1. Create New Module: `admin_workflow`
Create a new module at `app/modules/admin_workflow/` with the following files:

#### File: `app/modules/admin_workflow/__init__.py`
```python
"""
Admin Workflow Module
Handles disaster management workflow with agent integration
"""
```

#### File: `app/modules/admin_workflow/models.py`
Create SQLAlchemy models for:
- **AdminUser** - Admin account management
  - user_id (UUID, PK)
  - email (String, unique)
  - password_hash (String)
  - full_name (String)
  - org_name (String)
  - role (String: 'admin' or 'super_admin')
  - is_active (Boolean)
  - created_at, updated_at (Timestamp)

- **ThresholdBreachAlert** - Alerts from Data Collector Agent
  - alert_id (UUID, PK)
  - sensor_type (String: temperature, rainfall, seismic, wind_speed, water_level)
  - latitude, longitude (Numeric)
  - location_name, province (String)
  - current_value, threshold_value, breach_percentage (Numeric)
  - severity (String: LOW, MEDIUM, HIGH, CRITICAL)
  - data_source (String)
  - status (String: NEW, ACKNOWLEDGED, ANALYZING, RESOLVED)
  - acknowledged_by (UUID, FK to AdminUser)
  - acknowledged_at (Timestamp)
  - created_at, updated_at (Timestamp)

- **RiskAnalysis** - Risk analysis results
  - analysis_id (UUID, PK)
  - alert_id (UUID, FK to ThresholdBreachAlert, cascade delete)
  - risk_score (Integer, 0-100)
  - risk_level (String: LOW, MEDIUM, HIGH, CRITICAL)
  - disaster_type (String: FLOOD, EARTHQUAKE, HEATWAVE, STORM, DROUGHT)
  - affected_area_km2 (Numeric)
  - estimated_population_affected (Integer)
  - confidence_score (Integer, 0-100)
  - analysis_summary (Text)
  - detailed_analysis (JSONB)
  - recommended_actions (JSONB)
  - status (String: PENDING, COMPLETED, FAILED)
  - requested_by (UUID, FK to AdminUser)
  - requested_at, completed_at (Timestamp)
  - created_at, updated_at (Timestamp)

- **PrecautionaryMeasure** - Precautionary measures
  - precaution_id (UUID, PK)
  - analysis_id (UUID, FK to RiskAnalysis, cascade delete)
  - disaster_type (String)
  - risk_level (String)
  - overall_strategy (Text)
  - measures (JSONB)
  - timeline (JSONB)
  - estimated_cost (Numeric)
  - status (String: PENDING, GENERATED, APPROVED, IMPLEMENTED)
  - requested_by, approved_by (UUID, FK to AdminUser)
  - requested_at, generated_at, approved_at (Timestamp)
  - created_at, updated_at (Timestamp)

**Include proper relationships, indexes, and check constraints.**

#### File: `app/modules/admin_workflow/schemas.py`
Create Pydantic schemas for request/response validation:

**Admin Authentication:**
- AdminCreateRequest (email, password, org_name, full_name)
- AdminLoginRequest (email, password)
- AdminAuthResponse (user_id, email, org_name, role, access_token, refresh_token)

**Threshold Alerts:**
- LocationData (latitude, longitude, location_name, province)
- ThresholdAlertCreate (sensor_type, location, current_value, threshold_value, breach_percentage, severity, data_source)
- ThresholdAlertResponse (all alert fields)
- ThresholdAlertListResponse (alerts list, total_count, unacknowledged_count)

**Risk Analysis:**
- SensorData (sensor_type, current_value, threshold_value)
- RiskAnalysisRequest (alert_id, location, sensor_data, historical_data)
- DetailedAnalysis (severity_factors, vulnerability_assessment, historical_comparison, prediction_model_output)
- RiskAnalysisResponse (all analysis fields)
- RiskAnalysisListResponse (analyses list, total_count)

**Precautionary Measures:**
- RiskAnalysisData (risk_score, risk_level, disaster_type, affected_area_km2, estimated_population_affected)
- PrecautionaryRequest (analysis_id, risk_analysis_data, location)
- RequiredResources (personnel, vehicles, supplies)
- PrecautionaryMeasureDetail (measure_id, category, priority, title, description, target_population, estimated_duration_hours, required_resources, implementation_steps)
- Timeline (immediate_actions, short_term_actions, long_term_actions)
- PrecautionaryResponse (all precaution fields)
- PrecautionaryListResponse (precautions list, total_count)

**Generic:**
- SuccessResponse (success: bool)
- StatusResponse (id: UUID, status: str)

#### File: `app/modules/admin_workflow/agent_client.py`
Create HTTP client for agent communication:

```python
class AgentClient:
    def __init__(self):
        self.risk_analysis_url = settings.RISK_ANALYSIS_AGENT_URL
        self.precautionary_url = settings.PRECAUTIONARY_AGENT_URL
        self.timeout = 60.0
    
    async def request_risk_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to Risk Analysis Agent at /api/analyze"""
        # Use httpx.AsyncClient to POST to agent
        # Return agent response
    
    async def request_precautionary_measures(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to Precautionary Agent at /api/generate-measures"""
        # Use httpx.AsyncClient to POST to agent
        # Return agent response

agent_client = AgentClient()  # Singleton
```

#### File: `app/modules/admin_workflow/services.py`
Create service layer with business logic:

**AdminAuthService:**
- `hash_password(password: str) -> str` - Hash password with bcrypt
- `verify_password(plain_password: str, hashed_password: str) -> bool` - Verify password
- `create_admin(db: Session, data: AdminCreateRequest) -> AdminUser` - Create admin account
- `authenticate_admin(db: Session, email: str, password: str) -> Optional[AdminUser]` - Authenticate admin

**ThresholdAlertService:**
- `create_alert(db: Session, data: ThresholdAlertCreate) -> ThresholdBreachAlert` - Create alert
- `get_alerts(db: Session, status: Optional[str], severity: Optional[str], limit: int) -> tuple` - Get alerts with filters
- `get_alert_by_id(db: Session, alert_id: UUID) -> Optional[ThresholdBreachAlert]` - Get single alert
- `acknowledge_alert(db: Session, alert_id: UUID, admin_id: UUID) -> bool` - Acknowledge alert

**RiskAnalysisService:**
- `request_analysis(db: Session, data: RiskAnalysisRequest, admin_id: UUID) -> RiskAnalysis` - Request risk analysis (async)
  - Create PENDING record
  - Call agent_client.request_risk_analysis()
  - Update record with result
  - Handle errors
- `get_analysis_by_id(db: Session, analysis_id: UUID) -> Optional[RiskAnalysis]` - Get analysis
- `get_all_analyses(db: Session, status: Optional[str], limit: int) -> tuple` - Get all analyses

**PrecautionaryService:**
- `request_measures(db: Session, data: PrecautionaryRequest, admin_id: UUID) -> PrecautionaryMeasure` - Request measures (async)
  - Create PENDING record
  - Call agent_client.request_precautionary_measures()
  - Update record with result
  - Handle errors
- `get_measures_by_id(db: Session, precaution_id: UUID) -> Optional[PrecautionaryMeasure]` - Get measures
- `get_all_measures(db: Session, status: Optional[str], limit: int) -> tuple` - Get all measures
- `approve_measures(db: Session, precaution_id: UUID, admin_id: UUID) -> bool` - Approve measures

#### File: `app/modules/admin_workflow/routes.py`
Create FastAPI routes:

**Admin Authentication Routes:**
- `POST /api/admin/auth/create` - Create admin account
- `POST /api/admin/auth/login` - Admin login

**Threshold Alert Routes:**
- `POST /api/admin/threshold-alerts` - Create alert (requires agent API key in Authorization header)
- `GET /api/admin/threshold-alerts` - Get all alerts (requires admin auth)
- `GET /api/admin/threshold-alerts/{alert_id}` - Get single alert (requires admin auth)
- `POST /api/admin/threshold-alerts/{alert_id}/acknowledge` - Acknowledge alert (requires admin auth)

**Risk Analysis Routes:**
- `POST /api/admin/risk-analysis/request` - Request analysis (requires admin auth, async)
- `GET /api/admin/risk-analysis/{analysis_id}` - Get analysis result (requires admin auth)
- `GET /api/admin/risk-analysis` - Get all analyses (requires admin auth)

**Precautionary Measures Routes:**
- `POST /api/precautionary/request` - Request measures (requires admin auth, async)
- `GET /api/precautionary/{precaution_id}` - Get measures result (requires admin auth)
- `GET /api/precautionary` - Get all measures (requires admin auth)
- `POST /api/precautionary/{precaution_id}/approve` - Approve measures (requires admin auth)

**Use proper dependency injection for:**
- Database session: `db: Session = Depends(get_db)`
- Admin authentication: `current_user = Depends(get_current_admin_user)`
- Agent API key validation for threshold alerts endpoint

### 2. Create Database Migration

Create Alembic migration file in `migrations/versions/`:

```python
"""add disaster management workflow tables

Revision ID: xxx
Revises: previous_revision
Create Date: 2026-05-11
"""

def upgrade():
    # Create admin_users table with all columns, indexes, constraints
    # Create threshold_breach_alerts table with all columns, indexes, constraints, foreign keys
    # Create risk_analyses table with all columns, indexes, constraints, foreign keys
    # Create precautionary_measures table with all columns, indexes, constraints, foreign keys

def downgrade():
    # Drop all tables in reverse order
```

### 3. Update Configuration

**File: `app/core/config.py`**
Add these settings:
```python
RISK_ANALYSIS_AGENT_URL: str = os.getenv("RISK_ANALYSIS_AGENT_URL", "http://localhost:8002")
PRECAUTIONARY_AGENT_URL: str = os.getenv("PRECAUTIONARY_AGENT_URL", "http://localhost:8003")
AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "your-secure-agent-api-key")
```

**File: `.env.local`**
Add these variables:
```env
RISK_ANALYSIS_AGENT_URL=http://localhost:8002
PRECAUTIONARY_AGENT_URL=http://localhost:8003
AGENT_API_KEY=climasync-agent-secure-key-2026
```

### 4. Register Routes

**File: `main.py` or `app/main.py`**
Add:
```python
from app.modules.admin_workflow.routes import router as admin_workflow_router

app.include_router(
    admin_workflow_router,
    prefix="/api",
    tags=["Admin Workflow"]
)
```

### 5. Update CORS Configuration

Ensure CORS allows frontend at `http://localhost:3000`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Frontend API Expectations

The frontend is already calling these exact endpoints with these exact request/response formats:

### Admin Auth
- `POST /api/admin/auth/create` expects `AdminAuthResponse` with tokens
- `POST /api/admin/auth/login` expects `AdminAuthResponse` with tokens

### Threshold Alerts
- `POST /api/admin/threshold-alerts` expects `{alert_id, status, created_at}`
- `GET /api/admin/threshold-alerts?status=NEW&limit=50` expects `ThresholdAlertListResponse`
- `GET /api/admin/threshold-alerts/{alert_id}` expects `ThresholdAlertResponse`
- `POST /api/admin/threshold-alerts/{alert_id}/acknowledge` expects `{success: true}`

### Risk Analysis
- `POST /api/admin/risk-analysis/request` expects `{analysis_id, status: "PENDING"}`
- `GET /api/admin/risk-analysis/{analysis_id}` expects `RiskAnalysisResponse`
- Frontend polls this endpoint every 2 seconds until status is COMPLETED or FAILED

### Precautionary Measures
- `POST /api/precautionary/request` expects `{precaution_id, status: "PENDING"}`
- `GET /api/precautionary/{precaution_id}` expects `PrecautionaryResponse`
- Frontend polls this endpoint every 2 seconds until status is GENERATED

## Agent Integration

### Risk Analysis Agent (Port 8002)
**Endpoint:** `POST http://localhost:8002/api/analyze`

**Request:**
```json
{
    "alert_id": "uuid",
    "location": {"latitude": 24.8607, "longitude": 67.0011, "location_name": "Karachi", "province": "Sindh"},
    "sensor_data": {"sensor_type": "rainfall", "current_value": 150.5, "threshold_value": 100.0},
    "historical_data": {}
}
```

**Expected Response:**
```json
{
    "risk_score": 85,
    "risk_level": "HIGH",
    "disaster_type": "FLOOD",
    "affected_area_km2": 250.5,
    "estimated_population_affected": 50000,
    "confidence_score": 92,
    "analysis_summary": "High risk of urban flooding...",
    "detailed_analysis": {
        "severity_factors": ["Rainfall 50% above threshold", "Poor drainage"],
        "vulnerability_assessment": "Urban area with limited flood defenses",
        "historical_comparison": "Similar event in 2020",
        "prediction_model_output": {}
    },
    "recommended_actions": ["Evacuate low-lying areas", "Deploy emergency teams"]
}
```

### Precautionary Agent (Port 8003)
**Endpoint:** `POST http://localhost:8003/api/generate-measures`

**Request:**
```json
{
    "analysis_id": "uuid",
    "risk_analysis_data": {
        "risk_score": 85,
        "risk_level": "HIGH",
        "disaster_type": "FLOOD",
        "affected_area_km2": 250.5,
        "estimated_population_affected": 50000
    },
    "location": {"latitude": 24.8607, "longitude": 67.0011, "location_name": "Karachi", "province": "Sindh"}
}
```

**Expected Response:**
```json
{
    "overall_strategy": "Multi-phase response focusing on immediate evacuation...",
    "measures": [
        {
            "measure_id": "uuid",
            "category": "EVACUATION",
            "priority": "IMMEDIATE",
            "title": "Evacuate Low-Lying Areas",
            "description": "Immediate evacuation of residents...",
            "target_population": 15000,
            "estimated_duration_hours": 6,
            "required_resources": {
                "personnel": 200,
                "vehicles": 50,
                "supplies": ["Emergency kits", "Medical supplies"]
            },
            "implementation_steps": ["Activate alert system", "Deploy teams"]
        }
    ],
    "timeline": {
        "immediate_actions": ["Activate alerts"],
        "short_term_actions": ["Set up shelters"],
        "long_term_actions": ["Infrastructure repair"]
    },
    "estimated_cost": 5000000.00
}
```

## Important Implementation Notes

1. **Use existing auth utilities** from `app/core/auth.py` for JWT token generation and validation
2. **Use existing database setup** from `app/core/database.py` for session management
3. **Follow existing code patterns** in other modules (auth, admin, etc.)
4. **Use passlib with bcrypt** for password hashing
5. **Use httpx** for async HTTP requests to agents
6. **Add proper error handling** with try-catch blocks
7. **Add logging** using Python's logging module
8. **Use UUID** for all primary keys
9. **Use JSONB** for flexible JSON storage in PostgreSQL
10. **Add proper indexes** for performance (status, created_at, foreign keys)

## Testing After Implementation

1. Run migrations: `alembic upgrade head`
2. Start backend: `uvicorn main:app --reload --port 8000`
3. Test admin account creation:
```bash
curl -X POST http://localhost:8000/api/admin/auth/create \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Test123!","org_name":"NDMA","full_name":"Test Admin"}'
```

4. Test alert creation (simulate Data Collector Agent):
```bash
curl -X POST http://localhost:8000/api/admin/threshold-alerts \
  -H "Authorization: Bearer climasync-agent-secure-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"sensor_type":"rainfall","location":{"latitude":24.8607,"longitude":67.0011,"location_name":"Karachi","province":"Sindh"},"current_value":150.5,"threshold_value":100.0,"breach_percentage":50.5,"severity":"HIGH","data_source":"PMD Station"}'
```

## Success Criteria

✅ All 13 API endpoints working
✅ Database tables created with proper relationships
✅ Admin authentication with JWT tokens
✅ Agent communication working (even with dummy responses)
✅ Proper error handling and validation
✅ Frontend can successfully complete the full workflow

## Questions to Ask Me

If you need clarification on:
- Existing auth system implementation
- Database connection setup
- JWT token generation/validation
- Existing code patterns to follow
- Any other project-specific details

Please ask before implementing!

---

**Now please implement this complete backend workflow following the structure and requirements above.**
