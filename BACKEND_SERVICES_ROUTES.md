# Backend Services and Routes Implementation

## 5. Services Layer

**File:** `app/modules/admin_workflow/services.py`

```python
"""
Admin Workflow Services
Business logic for disaster management workflow
"""

import logging
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from passlib.context import CryptContext

from app.modules.admin_workflow.models import (
    AdminUser,
    ThresholdBreachAlert,
    RiskAnalysis,
    PrecautionaryMeasure
)
from app.modules.admin_workflow.schemas import (
    AdminCreateRequest,
    ThresholdAlertCreate,
    RiskAnalysisRequest,
    PrecautionaryRequest
)
from app.modules.admin_workflow.agent_client import agent_client

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Admin Authentication Services
# ============================================================================

class AdminAuthService:
    """Service for admin authentication"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_admin(db: Session, data: AdminCreateRequest) -> AdminUser:
        """Create a new admin user"""
        # Check if email already exists
        existing_user = db.query(AdminUser).filter(AdminUser.email == data.email).first()
        if existing_user:
            raise ValueError("Email already registered")

        # Create admin user
        admin_user = AdminUser(
            email=data.email,
            password_hash=AdminAuthService.hash_password(data.password),
            full_name=data.full_name,
            org_name=data.org_name,
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return admin_user

    @staticmethod
    def authenticate_admin(db: Session, email: str, password: str) -> Optional[AdminUser]:
        """Authenticate an admin user"""
        admin_user = db.query(AdminUser).filter(AdminUser.email == email).first()
        if not admin_user:
            return None
        if not AdminAuthService.verify_password(password, admin_user.password_hash):
            return None
        if not admin_user.is_active:
            raise ValueError("Account is disabled")
        return admin_user


# ============================================================================
# Threshold Alert Services
# ============================================================================

class ThresholdAlertService:
    """Service for threshold breach alerts"""

    @staticmethod
    def create_alert(db: Session, data: ThresholdAlertCreate) -> ThresholdBreachAlert:
        """Create a new threshold breach alert"""
        alert = ThresholdBreachAlert(
            sensor_type=data.sensor_type,
            latitude=data.location.latitude,
            longitude=data.location.longitude,
            location_name=data.location.location_name,
            province=data.location.province,
            current_value=data.current_value,
            threshold_value=data.threshold_value,
            breach_percentage=data.breach_percentage,
            severity=data.severity,
            data_source=data.data_source,
            status="NEW"
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(f"Created threshold alert: {alert.alert_id}")
        return alert

    @staticmethod
    def get_alerts(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> tuple[List[ThresholdBreachAlert], int, int]:
        """Get threshold alerts with filters"""
        query = db.query(ThresholdBreachAlert)

        if status:
            query = query.filter(ThresholdBreachAlert.status == status)
        if severity:
            query = query.filter(ThresholdBreachAlert.severity == severity)

        total_count = query.count()
        unacknowledged_count = db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.status == "NEW"
        ).count()

        alerts = query.order_by(desc(ThresholdBreachAlert.created_at)).limit(limit).all()
        return alerts, total_count, unacknowledged_count

    @staticmethod
    def get_alert_by_id(db: Session, alert_id: UUID) -> Optional[ThresholdBreachAlert]:
        """Get a single alert by ID"""
        return db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.alert_id == alert_id
        ).first()

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: UUID, admin_id: UUID) -> bool:
        """Acknowledge a threshold alert"""
        alert = ThresholdAlertService.get_alert_by_id(db, alert_id)
        if not alert:
            return False

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = admin_id
        alert.acknowledged_at = datetime.utcnow()
        db.commit()
        logger.info(f"Alert {alert_id} acknowledged by admin {admin_id}")
        return True


# ============================================================================
# Risk Analysis Services
# ============================================================================

class RiskAnalysisService:
    """Service for risk analysis"""

    @staticmethod
    async def request_analysis(
        db: Session,
        data: RiskAnalysisRequest,
        admin_id: UUID
    ) -> RiskAnalysis:
        """Request risk analysis from Risk Analysis Agent"""
        # Create pending analysis record
        analysis = RiskAnalysis(
            alert_id=data.alert_id,
            risk_score=0,
            risk_level="PENDING",
            disaster_type="UNKNOWN",
            affected_area_km2=0,
            estimated_population_affected=0,
            confidence_score=0,
            analysis_summary="Analysis in progress...",
            detailed_analysis={},
            recommended_actions=[],
            status="PENDING",
            requested_by=admin_id
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # Update alert status
        alert = db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.alert_id == data.alert_id
        ).first()
        if alert:
            alert.status = "ANALYZING"
            db.commit()

        # Send request to Risk Analysis Agent (async)
        try:
            agent_data = {
                "alert_id": str(data.alert_id),
                "location": {
                    "latitude": data.location.latitude,
                    "longitude": data.location.longitude,
                    "location_name": data.location.location_name,
                    "province": data.location.province
                },
                "sensor_data": {
                    "sensor_type": data.sensor_data.sensor_type,
                    "current_value": data.sensor_data.current_value,
                    "threshold_value": data.sensor_data.threshold_value
                },
                "historical_data": data.historical_data or {}
            }

            result = await agent_client.request_risk_analysis(agent_data)

            # Update analysis with result
            analysis.risk_score = result.get("risk_score", 0)
            analysis.risk_level = result.get("risk_level", "UNKNOWN")
            analysis.disaster_type = result.get("disaster_type", "UNKNOWN")
            analysis.affected_area_km2 = result.get("affected_area_km2", 0)
            analysis.estimated_population_affected = result.get("estimated_population_affected", 0)
            analysis.confidence_score = result.get("confidence_score", 0)
            analysis.analysis_summary = result.get("analysis_summary", "")
            analysis.detailed_analysis = result.get("detailed_analysis", {})
            analysis.recommended_actions = result.get("recommended_actions", [])
            analysis.status = "COMPLETED"
            analysis.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(analysis)

            logger.info(f"Risk analysis {analysis.analysis_id} completed")

        except Exception as e:
            logger.error(f"Risk analysis failed: {str(e)}")
            analysis.status = "FAILED"
            analysis.analysis_summary = f"Analysis failed: {str(e)}"
            db.commit()

        return analysis

    @staticmethod
    def get_analysis_by_id(db: Session, analysis_id: UUID) -> Optional[RiskAnalysis]:
        """Get risk analysis by ID"""
        return db.query(RiskAnalysis).filter(
            RiskAnalysis.analysis_id == analysis_id
        ).first()

    @staticmethod
    def get_all_analyses(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50
    ) -> tuple[List[RiskAnalysis], int]:
        """Get all risk analyses"""
        query = db.query(RiskAnalysis)

        if status:
            query = query.filter(RiskAnalysis.status == status)

        total_count = query.count()
        analyses = query.order_by(desc(RiskAnalysis.created_at)).limit(limit).all()
        return analyses, total_count


# ============================================================================
# Precautionary Measures Services
# ============================================================================

class PrecautionaryService:
    """Service for precautionary measures"""

    @staticmethod
    async def request_measures(
        db: Session,
        data: PrecautionaryRequest,
        admin_id: UUID
    ) -> PrecautionaryMeasure:
        """Request precautionary measures from Precautionary Agent"""
        # Create pending precaution record
        precaution = PrecautionaryMeasure(
            analysis_id=data.analysis_id,
            disaster_type=data.risk_analysis_data.disaster_type,
            risk_level=data.risk_analysis_data.risk_level,
            overall_strategy="Generating precautionary measures...",
            measures=[],
            timeline={},
            status="PENDING",
            requested_by=admin_id
        )
        db.add(precaution)
        db.commit()
        db.refresh(precaution)

        # Send request to Precautionary Agent (async)
        try:
            agent_data = {
                "analysis_id": str(data.analysis_id),
                "risk_analysis_data": {
                    "risk_score": data.risk_analysis_data.risk_score,
                    "risk_level": data.risk_analysis_data.risk_level,
                    "disaster_type": data.risk_analysis_data.disaster_type,
                    "affected_area_km2": data.risk_analysis_data.affected_area_km2,
                    "estimated_population_affected": data.risk_analysis_data.estimated_population_affected
                },
                "location": {
                    "latitude": data.location.latitude,
                    "longitude": data.location.longitude,
                    "location_name": data.location.location_name,
                    "province": data.location.province
                }
            }

            result = await agent_client.request_precautionary_measures(agent_data)

            # Update precaution with result
            precaution.overall_strategy = result.get("overall_strategy", "")
            precaution.measures = result.get("measures", [])
            precaution.timeline = result.get("timeline", {})
            precaution.estimated_cost = result.get("estimated_cost")
            precaution.status = "GENERATED"
            precaution.generated_at = datetime.utcnow()
            db.commit()
            db.refresh(precaution)

            logger.info(f"Precautionary measures {precaution.precaution_id} generated")

        except Exception as e:
            logger.error(f"Precautionary measures generation failed: {str(e)}")
            precaution.status = "FAILED"
            precaution.overall_strategy = f"Generation failed: {str(e)}"
            db.commit()

        return precaution

    @staticmethod
    def get_measures_by_id(db: Session, precaution_id: UUID) -> Optional[PrecautionaryMeasure]:
        """Get precautionary measures by ID"""
        return db.query(PrecautionaryMeasure).filter(
            PrecautionaryMeasure.precaution_id == precaution_id
        ).first()

    @staticmethod
    def get_all_measures(
        db: Session,
        status: Optional[str] = None,
        limit: int = 50
    ) -> tuple[List[PrecautionaryMeasure], int]:
        """Get all precautionary measures"""
        query = db.query(PrecautionaryMeasure)

        if status:
            query = query.filter(PrecautionaryMeasure.status == status)

        total_count = query.count()
        precautions = query.order_by(desc(PrecautionaryMeasure.created_at)).limit(limit).all()
        return precautions, total_count

    @staticmethod
    def approve_measures(db: Session, precaution_id: UUID, admin_id: UUID) -> bool:
        """Approve precautionary measures"""
        precaution = PrecautionaryService.get_measures_by_id(db, precaution_id)
        if not precaution:
            return False

        precaution.status = "APPROVED"
        precaution.approved_by = admin_id
        precaution.approved_at = datetime.utcnow()
        db.commit()
        logger.info(f"Precautionary measures {precaution_id} approved by admin {admin_id}")
        return True
```

---

## 6. API Routes

**File:** `app/modules/admin_workflow/routes.py`

```python
"""
Admin Workflow Routes
FastAPI routes for disaster management workflow
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_admin_user, create_access_token, create_refresh_token
from app.core.config import settings
from app.modules.admin_workflow.schemas import *
from app.modules.admin_workflow.services import (
    AdminAuthService,
    ThresholdAlertService,
    RiskAnalysisService,
    PrecautionaryService
)

router = APIRouter()


# ============================================================================
# Admin Authentication Routes
# ============================================================================

@router.post("/admin/auth/create", response_model=AdminAuthResponse, status_code=status.HTTP_201_CREATED)
def create_admin_account(
    data: AdminCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new admin account"""
    try:
        admin_user = AdminAuthService.create_admin(db, data)
        
        # Generate tokens
        access_token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role})
        refresh_token = create_refresh_token({"sub": str(admin_user.user_id)})
        
        return AdminAuthResponse(
            user_id=admin_user.user_id,
            email=admin_user.email,
            org_name=admin_user.org_name,
            role=admin_user.role,
            access_token=access_token,
            refresh_token=refresh_token
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin/auth/login", response_model=AdminAuthResponse)
def admin_login(
    data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """Admin login"""
    try:
        admin_user = AdminAuthService.authenticate_admin(db, data.email, data.password)
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate tokens
        access_token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role})
        refresh_token = create_refresh_token({"sub": str(admin_user.user_id)})
        
        return AdminAuthResponse(
            user_id=admin_user.user_id,
            email=admin_user.email,
            org_name=admin_user.org_name,
            role=admin_user.role,
            access_token=access_token,
            refresh_token=refresh_token
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ============================================================================
# Threshold Alert Routes
# ============================================================================

@router.post("/admin/threshold-alerts", status_code=status.HTTP_201_CREATED)
def create_threshold_alert(
    data: ThresholdAlertCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Receive threshold breach alert from Data Collector Agent
    Requires agent API key in Authorization header
    """
    # Verify agent API key
    if authorization != f"Bearer {settings.AGENT_API_KEY}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent API key"
        )
    
    alert = ThresholdAlertService.create_alert(db, data)
    return {
        "alert_id": alert.alert_id,
        "status": alert.status,
        "created_at": alert.created_at
    }


@router.get("/admin/threshold-alerts", response_model=ThresholdAlertListResponse)
def get_threshold_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get all threshold breach alerts for admin"""
    alerts, total_count, unacknowledged_count = ThresholdAlertService.get_alerts(
        db, status, severity, limit
    )
    
    return ThresholdAlertListResponse(
        alerts=[
            ThresholdAlertResponse(
                alert_id=alert.alert_id,
                sensor_type=alert.sensor_type,
                location=LocationData(
                    latitude=float(alert.latitude),
                    longitude=float(alert.longitude),
                    location_name=alert.location_name,
                    province=alert.province
                ),
                current_value=float(alert.current_value),
                threshold_value=float(alert.threshold_value),
                breach_percentage=float(alert.breach_percentage),
                severity=alert.severity,
                timestamp=alert.created_at,
                data_source=alert.data_source,
                status=alert.status
            )
            for alert in alerts
        ],
        total_count=total_count,
        unacknowledged_count=unacknowledged_count
    )


@router.get("/admin/threshold-alerts/{alert_id}", response_model=ThresholdAlertResponse)
def get_threshold_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get single threshold alert details"""
    alert = ThresholdAlertService.get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    return ThresholdAlertResponse(
        alert_id=alert.alert_id,
        sensor_type=alert.sensor_type,
        location=LocationData(
            latitude=float(alert.latitude),
            longitude=float(alert.longitude),
            location_name=alert.location_name,
            province=alert.province
        ),
        current_value=float(alert.current_value),
        threshold_value=float(alert.threshold_value),
        breach_percentage=float(alert.breach_percentage),
        severity=alert.severity,
        timestamp=alert.created_at,
        data_source=alert.data_source,
        status=alert.status
    )


@router.post("/admin/threshold-alerts/{alert_id}/acknowledge", response_model=SuccessResponse)
def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Acknowledge a threshold alert"""
    success = ThresholdAlertService.acknowledge_alert(db, alert_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    return SuccessResponse(success=True)


# ============================================================================
# Risk Analysis Routes
# ============================================================================

@router.post("/admin/risk-analysis/request", status_code=status.HTTP_202_ACCEPTED)
async def request_risk_analysis(
    data: RiskAnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Request risk analysis from Risk Analysis Agent"""
    analysis = await RiskAnalysisService.request_analysis(db, data, current_user.user_id)
    return StatusResponse(id=analysis.analysis_id, status=analysis.status)


@router.get("/admin/risk-analysis/{analysis_id}", response_model=RiskAnalysisResponse)
def get_risk_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get risk analysis result"""
    analysis = RiskAnalysisService.get_analysis_by_id(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    return RiskAnalysisResponse(
        analysis_id=analysis.analysis_id,
        alert_id=analysis.alert_id,
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        disaster_type=analysis.disaster_type,
        affected_area_km2=float(analysis.affected_area_km2),
        estimated_population_affected=analysis.estimated_population_affected,
        confidence_score=analysis.confidence_score,
        analysis_summary=analysis.analysis_summary,
        detailed_analysis=DetailedAnalysis(**analysis.detailed_analysis),
        recommended_actions=analysis.recommended_actions,
        timestamp=analysis.created_at,
        status=analysis.status
    )


@router.get("/admin/risk-analysis", response_model=RiskAnalysisListResponse)
def get_all_risk_analyses(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get all risk analyses"""
    analyses, total_count = RiskAnalysisService.get_all_analyses(db, status, limit)
    
    return RiskAnalysisListResponse(
        analyses=[
            RiskAnalysisResponse(
                analysis_id=a.analysis_id,
                alert_id=a.alert_id,
                risk_score=a.risk_score,
                risk_level=a.risk_level,
                disaster_type=a.disaster_type,
                affected_area_km2=float(a.affected_area_km2),
                estimated_population_affected=a.estimated_population_affected,
                confidence_score=a.confidence_score,
                analysis_summary=a.analysis_summary,
                detailed_analysis=DetailedAnalysis(**a.detailed_analysis),
                recommended_actions=a.recommended_actions,
                timestamp=a.created_at,
                status=a.status
            )
            for a in analyses
        ],
        total_count=total_count
    )


# ============================================================================
# Precautionary Measures Routes
# ============================================================================

@router.post("/precautionary/request", status_code=status.HTTP_202_ACCEPTED)
async def request_precautionary_measures(
    data: PrecautionaryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Request precautionary measures from Precautionary Agent"""
    precaution = await PrecautionaryService.request_measures(db, data, current_user.user_id)
    return StatusResponse(id=precaution.precaution_id, status=precaution.status)


@router.get("/precautionary/{precaution_id}", response_model=PrecautionaryResponse)
def get_precautionary_measures(
    precaution_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get precautionary measures result"""
    precaution = PrecautionaryService.get_measures_by_id(db, precaution_id)
    if not precaution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Precautionary measures not found")
    
    return PrecautionaryResponse(
        precaution_id=precaution.precaution_id,
        analysis_id=precaution.analysis_id,
        disaster_type=precaution.disaster_type,
        risk_level=precaution.risk_level,
        measures=[PrecautionaryMeasureDetail(**m) for m in precaution.measures],
        overall_strategy=precaution.overall_strategy,
        timeline=Timeline(**precaution.timeline),
        estimated_cost=float(precaution.estimated_cost) if precaution.estimated_cost else None,
        generated_at=precaution.generated_at or precaution.created_at,
        status=precaution.status
    )


@router.get("/precautionary", response_model=PrecautionaryListResponse)
def get_all_precautionary_measures(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get all precautionary measures"""
    precautions, total_count = PrecautionaryService.get_all_measures(db, status, limit)
    
    return PrecautionaryListResponse(
        precautions=[
            PrecautionaryResponse(
                precaution_id=p.precaution_id,
                analysis_id=p.analysis_id,
                disaster_type=p.disaster_type,
                risk_level=p.risk_level,
                measures=[PrecautionaryMeasureDetail(**m) for m in p.measures],
                overall_strategy=p.overall_strategy,
                timeline=Timeline(**p.timeline),
                estimated_cost=float(p.estimated_cost) if p.estimated_cost else None,
                generated_at=p.generated_at or p.created_at,
                status=p.status
            )
            for p in precautions
        ],
        total_count=total_count
    )


@router.post("/precautionary/{precaution_id}/approve", response_model=SuccessResponse)
def approve_precautionary_measures(
    precaution_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Approve precautionary measures"""
    success = PrecautionaryService.approve_measures(db, precaution_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Precautionary measures not found")
    
    return SuccessResponse(success=True)
```

---

## 7. Configuration Updates

**File:** `app/core/config.py` (Add these settings)

```python
# Agent Microservice URLs
RISK_ANALYSIS_AGENT_URL: str = os.getenv("RISK_ANALYSIS_AGENT_URL", "http://localhost:8002")
PRECAUTIONARY_AGENT_URL: str = os.getenv("PRECAUTIONARY_AGENT_URL", "http://localhost:8003")
AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "your-secure-agent-api-key")
```

**File:** `.env.local` (Add these variables)

```env
# Agent Microservice Configuration
RISK_ANALYSIS_AGENT_URL=http://localhost:8002
PRECAUTIONARY_AGENT_URL=http://localhost:8003
AGENT_API_KEY=your-secure-agent-api-key-change-in-production
```

---

## 8. Main App Registration

**File:** `main.py` or `app/main.py` (Add route registration)

```python
from app.modules.admin_workflow.routes import router as admin_workflow_router

# Register admin workflow routes
app.include_router(
    admin_workflow_router,
    prefix="/api",
    tags=["Admin Workflow"]
)
```

---

## Testing

### Test with cURL

```bash
# 1. Create Admin Account
curl -X POST http://localhost:8000/api/admin/auth/create \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@climasync.ai",
    "password": "SecurePass123!",
    "org_name": "NDMA",
    "full_name": "John Doe"
  }'

# 2. Simulate Data Collector Agent sending alert
curl -X POST http://localhost:8000/api/admin/threshold-alerts \
  -H "Authorization: Bearer your-secure-agent-api-key" \
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
    "data_source": "PMD Weather Station"
  }'

# 3. Get alerts (use access_token from step 1)
curl -X GET http://localhost:8000/api/admin/threshold-alerts \
  -H "Authorization: Bearer <access_token>"
```

---

**Implementation Complete!** All backend code is now ready for deployment.
