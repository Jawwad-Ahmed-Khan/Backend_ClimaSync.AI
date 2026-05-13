# Backend API Implementation Guide
## ClimaSync.AI - Disaster Management Workflow

This document provides complete backend API implementation for the disaster management workflow integrating Data Collector Agent, Risk Analysis Agent, and Precautionary Agent.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [API Endpoints](#api-endpoints)
4. [Agent Integration](#agent-integration)
5. [Implementation Steps](#implementation-steps)

---

## Architecture Overview

### Workflow Flow
```
Data Collector Agent → Backend → Admin Frontend
                          ↓
                    Risk Analysis Agent
                          ↓
                    Backend → Admin Frontend
                          ↓
                    Precautionary Agent
                          ↓
                    Backend → Admin Frontend
```

### Technology Stack
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Agent Communication**: HTTP REST APIs
- **Authentication**: JWT Bearer Tokens

---

## Database Schema

### 1. Admin Users Table
```sql
CREATE TABLE admin_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    org_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin' CHECK (role IN ('admin', 'super_admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_users_email ON admin_users(email);
CREATE INDEX idx_admin_users_role ON admin_users(role);
```

### 2. Threshold Breach Alerts Table
```sql
CREATE TABLE threshold_breach_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sensor_type VARCHAR(50) NOT NULL CHECK (sensor_type IN ('temperature', 'rainfall', 'seismic', 'wind_speed', 'water_level')),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    location_name VARCHAR(255) NOT NULL,
    province VARCHAR(100) NOT NULL,
    current_value DECIMAL(10, 2) NOT NULL,
    threshold_value DECIMAL(10, 2) NOT NULL,
    breach_percentage DECIMAL(5, 2) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    data_source VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'NEW' CHECK (status IN ('NEW', 'ACKNOWLEDGED', 'ANALYZING', 'RESOLVED')),
    acknowledged_by UUID REFERENCES admin_users(user_id),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_status ON threshold_breach_alerts(status);
CREATE INDEX idx_alerts_severity ON threshold_breach_alerts(severity);
CREATE INDEX idx_alerts_created_at ON threshold_breach_alerts(created_at DESC);
CREATE INDEX idx_alerts_location ON threshold_breach_alerts(latitude, longitude);
```

### 3. Risk Analyses Table
```sql
CREATE TABLE risk_analyses (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES threshold_breach_alerts(alert_id) ON DELETE CASCADE,
    risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    disaster_type VARCHAR(50) NOT NULL CHECK (disaster_type IN ('FLOOD', 'EARTHQUAKE', 'HEATWAVE', 'STORM', 'DROUGHT')),
    affected_area_km2 DECIMAL(10, 2) NOT NULL,
    estimated_population_affected INTEGER NOT NULL,
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
    analysis_summary TEXT NOT NULL,
    detailed_analysis JSONB NOT NULL,
    recommended_actions JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED')),
    requested_by UUID REFERENCES admin_users(user_id),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_risk_analyses_alert_id ON risk_analyses(alert_id);
CREATE INDEX idx_risk_analyses_status ON risk_analyses(status);
CREATE INDEX idx_risk_analyses_created_at ON risk_analyses(created_at DESC);
```

### 4. Precautionary Measures Table
```sql
CREATE TABLE precautionary_measures (
    precaution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES risk_analyses(analysis_id) ON DELETE CASCADE,
    disaster_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    overall_strategy TEXT NOT NULL,
    measures JSONB NOT NULL,
    timeline JSONB NOT NULL,
    estimated_cost DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'GENERATED', 'APPROVED', 'IMPLEMENTED')),
    requested_by UUID REFERENCES admin_users(user_id),
    approved_by UUID REFERENCES admin_users(user_id),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_at TIMESTAMP,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_precautionary_analysis_id ON precautionary_measures(analysis_id);
CREATE INDEX idx_precautionary_status ON precautionary_measures(status);
CREATE INDEX idx_precautionary_created_at ON precautionary_measures(created_at DESC);
```

---

## API Endpoints

### 1. Admin Authentication

#### POST `/api/admin/auth/create`
Create a new admin account.

**Request Body:**
```json
{
    "email": "admin@climasync.ai",
    "password": "SecurePass123!",
    "org_name": "National Disaster Management Authority",
    "full_name": "John Doe"
}
```

**Response (201):**
```json
{
    "user_id": "uuid",
    "email": "admin@climasync.ai",
    "org_name": "National Disaster Management Authority",
    "role": "admin",
    "access_token": "jwt_token",
    "refresh_token": "jwt_refresh_token"
}
```

#### POST `/api/admin/auth/login`
Admin login.

**Request Body:**
```json
{
    "email": "admin@climasync.ai",
    "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
    "user_id": "uuid",
    "email": "admin@climasync.ai",
    "org_name": "National Disaster Management Authority",
    "role": "admin",
    "access_token": "jwt_token",
    "refresh_token": "jwt_refresh_token"
}
```

---

### 2. Threshold Breach Alerts

#### POST `/api/admin/threshold-alerts` (Internal - From Data Collector Agent)
Receive threshold breach alert from Data Collector Agent.

**Headers:**
```
Authorization: Bearer <agent_api_key>
Content-Type: application/json
```

**Request Body:**
```json
{
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
}
```

**Response (201):**
```json
{
    "alert_id": "uuid",
    "status": "NEW",
    "created_at": "2026-05-11T10:30:00Z"
}
```

#### GET `/api/admin/threshold-alerts`
Get all threshold breach alerts for admin.

**Query Parameters:**
- `status` (optional): Filter by status (NEW, ACKNOWLEDGED, ANALYZING, RESOLVED)
- `severity` (optional): Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
- `limit` (optional): Number of results (default: 50)

**Response (200):**
```json
{
    "alerts": [
        {
            "alert_id": "uuid",
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
            "timestamp": "2026-05-11T10:30:00Z",
            "data_source": "PMD Weather Station KHI-001",
            "status": "NEW"
        }
    ],
    "total_count": 1,
    "unacknowledged_count": 1
}
```

#### GET `/api/admin/threshold-alerts/{alert_id}`
Get single threshold alert details.

**Response (200):**
```json
{
    "alert_id": "uuid",
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
    "timestamp": "2026-05-11T10:30:00Z",
    "data_source": "PMD Weather Station KHI-001",
    "status": "NEW"
}
```

#### POST `/api/admin/threshold-alerts/{alert_id}/acknowledge`
Acknowledge a threshold alert.

**Response (200):**
```json
{
    "success": true
}
```

---

### 3. Risk Analysis

#### POST `/api/admin/risk-analysis/request`
Request risk analysis from Risk Analysis Agent.

**Request Body:**
```json
{
    "alert_id": "uuid",
    "location": {
        "latitude": 24.8607,
        "longitude": 67.0011,
        "location_name": "Karachi",
        "province": "Sindh"
    },
    "sensor_data": {
        "sensor_type": "rainfall",
        "current_value": 150.5,
        "threshold_value": 100.0
    },
    "historical_data": {}
}
```

**Response (202):**
```json
{
    "analysis_id": "uuid",
    "status": "PENDING"
}
```

**Backend Process:**
1. Create risk analysis record with status PENDING
2. Send request to Risk Analysis Agent microservice
3. Risk Analysis Agent processes and returns result
4. Update risk analysis record with result and status COMPLETED

#### GET `/api/admin/risk-analysis/{analysis_id}`
Get risk analysis result.

**Response (200):**
```json
{
    "analysis_id": "uuid",
    "alert_id": "uuid",
    "risk_score": 85,
    "risk_level": "HIGH",
    "disaster_type": "FLOOD",
    "affected_area_km2": 250.5,
    "estimated_population_affected": 50000,
    "confidence_score": 92,
    "analysis_summary": "High risk of urban flooding in Karachi due to excessive rainfall...",
    "detailed_analysis": {
        "severity_factors": [
            "Rainfall 50% above threshold",
            "Poor drainage infrastructure",
            "High population density"
        ],
        "vulnerability_assessment": "Urban area with limited flood defenses...",
        "historical_comparison": "Similar event in 2020 affected 45,000 people...",
        "prediction_model_output": {}
    },
    "recommended_actions": [
        "Evacuate low-lying areas",
        "Deploy emergency response teams",
        "Activate flood warning systems"
    ],
    "timestamp": "2026-05-11T10:35:00Z",
    "status": "COMPLETED"
}
```

#### GET `/api/admin/risk-analysis`
Get all risk analyses.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Number of results (default: 50)

**Response (200):**
```json
{
    "analyses": [...],
    "total_count": 10
}
```

---

### 4. Precautionary Measures

#### POST `/api/precautionary/request`
Request precautionary measures from Precautionary Agent.

**Request Body:**
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
    "location": {
        "latitude": 24.8607,
        "longitude": 67.0011,
        "location_name": "Karachi",
        "province": "Sindh"
    }
}
```

**Response (202):**
```json
{
    "precaution_id": "uuid",
    "status": "PENDING"
}
```

**Backend Process:**
1. Create precautionary measures record with status PENDING
2. Send request to Precautionary Agent microservice
3. Precautionary Agent generates measures
4. Update precautionary measures record with result and status GENERATED

#### GET `/api/precautionary/{precaution_id}`
Get precautionary measures result.

**Response (200):**
```json
{
    "precaution_id": "uuid",
    "analysis_id": "uuid",
    "disaster_type": "FLOOD",
    "risk_level": "HIGH",
    "measures": [
        {
            "measure_id": "uuid",
            "category": "EVACUATION",
            "priority": "IMMEDIATE",
            "title": "Evacuate Low-Lying Areas",
            "description": "Immediate evacuation of residents in flood-prone zones...",
            "target_population": 15000,
            "estimated_duration_hours": 6,
            "required_resources": {
                "personnel": 200,
                "vehicles": 50,
                "supplies": ["Emergency kits", "Medical supplies", "Food packets"]
            },
            "implementation_steps": [
                "Activate emergency alert system",
                "Deploy evacuation teams",
                "Set up temporary shelters"
            ]
        }
    ],
    "overall_strategy": "Multi-phase response focusing on immediate evacuation...",
    "timeline": {
        "immediate_actions": ["Activate alerts", "Deploy teams"],
        "short_term_actions": ["Set up shelters", "Distribute supplies"],
        "long_term_actions": ["Infrastructure repair", "Flood prevention"]
    },
    "estimated_cost": 5000000.00,
    "generated_at": "2026-05-11T10:40:00Z",
    "status": "GENERATED"
}
```

#### GET `/api/precautionary`
Get all precautionary measures.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Number of results (default: 50)

**Response (200):**
```json
{
    "precautions": [...],
    "total_count": 5
}
```

#### POST `/api/precautionary/{precaution_id}/approve`
Approve precautionary measures.

**Response (200):**
```json
{
    "success": true
}
```

---

## Agent Integration

### 1. Data Collector Agent → Backend

**Agent Endpoint Configuration:**
```python
DATA_COLLECTOR_AGENT_URL = "http://localhost:8001"  # Data Collector Agent URL
BACKEND_WEBHOOK_URL = "http://localhost:8000/api/admin/threshold-alerts"
AGENT_API_KEY = "your-secure-agent-api-key"
```

**Data Collector Agent sends POST request to Backend:**
```python
import requests

def send_threshold_alert(alert_data):
    response = requests.post(
        f"{BACKEND_WEBHOOK_URL}",
        headers={
            "Authorization": f"Bearer {AGENT_API_KEY}",
            "Content-Type": "application/json"
        },
        json=alert_data
    )
    return response.json()
```

### 2. Backend → Risk Analysis Agent

**Risk Analysis Agent Configuration:**
```python
RISK_ANALYSIS_AGENT_URL = "http://localhost:8002"  # Risk Analysis Agent URL
RISK_ANALYSIS_ENDPOINT = "/api/analyze"
```

**Backend sends request to Risk Analysis Agent:**
```python
import requests
import asyncio

async def request_risk_analysis(analysis_data):
    response = requests.post(
        f"{RISK_ANALYSIS_AGENT_URL}{RISK_ANALYSIS_ENDPOINT}",
        headers={"Content-Type": "application/json"},
        json=analysis_data,
        timeout=60
    )
    return response.json()
```

### 3. Backend → Precautionary Agent

**Precautionary Agent Configuration:**
```python
PRECAUTIONARY_AGENT_URL = "http://localhost:8003"  # Precautionary Agent URL
PRECAUTIONARY_ENDPOINT = "/api/generate-measures"
```

**Backend sends request to Precautionary Agent:**
```python
import requests

async def request_precautionary_measures(precaution_data):
    response = requests.post(
        f"{PRECAUTIONARY_AGENT_URL}{PRECAUTIONARY_ENDPOINT}",
        headers={"Content-Type": "application/json"},
        json=precaution_data,
        timeout=60
    )
    return response.json()
```

---

## Implementation Steps

### Step 1: Database Setup
```bash
cd F:\ClimasyncAI_backend
# Run migration script
alembic revision --autogenerate -m "Add disaster management workflow tables"
alembic upgrade head
```

### Step 2: Create Backend Module Structure
```bash
cd F:\ClimasyncAI_backend\app\modules
mkdir -p admin_workflow
cd admin_workflow
touch __init__.py models.py schemas.py routes.py services.py
```

### Step 3: Implement Models (models.py)
See detailed implementation in next section.

### Step 4: Implement Schemas (schemas.py)
See detailed implementation in next section.

### Step 5: Implement Services (services.py)
See detailed implementation in next section.

### Step 6: Implement Routes (routes.py)
See detailed implementation in next section.

### Step 7: Register Routes in main.py
```python
from app.modules.admin_workflow.routes import router as admin_workflow_router

app.include_router(admin_workflow_router, prefix="/api", tags=["Admin Workflow"])
```

### Step 8: Configure Agent URLs in .env
```env
DATA_COLLECTOR_AGENT_URL=http://localhost:8001
RISK_ANALYSIS_AGENT_URL=http://localhost:8002
PRECAUTIONARY_AGENT_URL=http://localhost:8003
AGENT_API_KEY=your-secure-agent-api-key
```

### Step 9: Test with Dummy Data
Create test scripts to simulate agent responses.

### Step 10: Deploy and Monitor
Deploy backend and monitor agent communication.

---

## Next Steps

1. Implement the backend code files (models, schemas, services, routes)
2. Create database migration scripts
3. Set up agent communication endpoints
4. Test complete workflow with dummy data
5. Deploy to production

---

**Note:** Detailed implementation code for each file will be provided in separate files.
