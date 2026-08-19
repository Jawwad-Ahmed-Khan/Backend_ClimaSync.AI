"""HTTP controllers for disaster management workflow.

This module implements FastAPI route handlers for:
- Admin authentication (create account, login)
- Threshold alert management
- Risk analysis workflow
- Precautionary measures workflow

Controllers handle HTTP concerns: request parsing, response formatting,
status codes, and dependency injection.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.security import create_access_token, create_refresh_token
from app.modules.admin_workflow.dependencies import AgentApiKeyDep, CurrentAdminUser
from app.modules.admin_workflow.schemas import (
    AdminAuthResponse,
    AdminCreateRequest,
    AdminLoginRequest,
    AlertCreatedResponse,
    IncomingBreachPayload,
    RiskAnalysisListResponse,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    StatusResponse,
    SuccessResponse,
    ThresholdAlertListResponse,
    ThresholdAlertResponse,
)
from app.modules.admin_workflow.services import AdminAuthService, RiskAnalysisService, ThresholdAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Workflow"])


# ============================================================================
# Dependencies
# ============================================================================

DbDep = Annotated[Session, Depends(get_db)]


# ============================================================================
# Task 6.1: Admin Authentication Endpoints
# ============================================================================


@router.post(
    "/auth/create",
    response_model=AdminAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin account",
    description="Create a new admin account with email, password, organization name, and full name. "
    "Returns user details and JWT tokens for immediate authentication.",
)
async def create_admin_account(
    data: AdminCreateRequest,
    db: DbDep,
) -> AdminAuthResponse:
    """Create a new admin account.
    
    Requirements: 1.1, 1.3, 17.6
    """
    # Create admin account
    admin = await AdminAuthService.create_admin(
        db=db,
        email=data.email,
        password=data.password,
        org_name=data.org_name,
        full_name=data.full_name,
    )
    
    # Generate JWT tokens
    access_token = create_access_token(
        subject=str(admin.user_id),
        extra_claims={"role": admin.role},
    )
    refresh_token = create_refresh_token(subject=str(admin.user_id))
    
    return AdminAuthResponse(
        user_id=admin.user_id,
        email=admin.email,
        org_name=admin.org_name,
        role=admin.role,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/auth/login",
    response_model=AdminAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin login",
    description="Authenticate an admin user with email and password. "
    "Returns user details and JWT tokens on successful authentication.",
)
async def login_admin(
    data: AdminLoginRequest,
    db: DbDep,
) -> AdminAuthResponse:
    """Authenticate an admin user.
    
    Requirements: 2.1, 2.3, 2.6, 2.7, 17.8
    """
    # Authenticate admin
    admin = await AdminAuthService.authenticate_admin(
        db=db,
        email=data.email,
        password=data.password,
    )
    
    # Generate JWT tokens
    access_token = create_access_token(
        subject=str(admin.user_id),
        extra_claims={"role": admin.role},
    )
    refresh_token = create_refresh_token(subject=str(admin.user_id))
    
    return AdminAuthResponse(
        user_id=admin.user_id,
        email=admin.email,
        org_name=admin.org_name,
        role=admin.role,
        access_token=access_token,
        refresh_token=refresh_token,
    )




# ============================================================================
# Task 10.1: Threshold Alert Endpoints
# ============================================================================


@router.post(
    "/threshold-alerts",
    response_model=AlertCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create threshold alert",
    description="Create a new threshold breach alert from the Data Collection Service. "
    "Requires Agent API key authentication. Broadcasts alert via WebSocket to connected clients.",
)
async def create_threshold_alert(
    data: IncomingBreachPayload,
    db: DbDep,
    _: AgentApiKeyDep,
) -> AlertCreatedResponse:
    """Create a new threshold breach alert.
    
    This endpoint receives alerts from the Data Collection Service when
    sensor readings exceed predefined thresholds. The alert is stored in
    the database and immediately broadcast to all connected WebSocket clients.
    
    Requirements: 3.1, 3.2, 3.11, 12.2, 12.4, 12.7, 13.6
    """
    from app.websockets.manager import ws_manager
    
    # Map incoming breach payload to threshold alert format
    alert_data = {
        "sensor_type": data.disaster_kind,  # Map disaster_kind to sensor_type
        "latitude": data.latitude,
        "longitude": data.longitude,
        "location_name": data.location_name or "Unknown",
        "province": data.province or "Unknown",
        "current_value": data.observed_value,
        "threshold_value": data.threshold_value,
        "breach_percentage": ((data.observed_value - data.threshold_value) / data.threshold_value * 100),
        "severity": data.breach_severity.upper(),  # Map breach_severity to severity
        "data_source": data.source_api,
    }
    
    # Create alert in database
    alert = await ThresholdAlertService.create_alert(db=db, data=alert_data)
    
    # Broadcast to WebSocket clients
    await ws_manager.broadcast_alert({
        "alert_id": str(alert.alert_id),
        "breach_id": data.breach_id,
        "source_api": data.source_api,
        "disaster_kind": data.disaster_kind,
        "metric_name": data.metric_name,
        "location_name": data.location_name,
        "district": data.district,
        "province": data.province,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "observed_value": data.observed_value,
        "threshold_value": data.threshold_value,
        "breach_severity": data.breach_severity,
        "unit": data.unit,
        "observation_time": data.observation_time.isoformat(),
        "detected_at": data.detected_at.isoformat(),
        "is_forecast": data.is_forecast,
        "forecast_horizon_h": data.forecast_horizon_h,
        "seismic_event_id": data.seismic_event_id,
        "weather_location_id": data.weather_location_id,
        "gauge_id": data.gauge_id,
        "status": alert.status,
        "created_at": alert.created_at.isoformat(),
    })
    
    return AlertCreatedResponse(
        alert_id=alert.alert_id,
        status=alert.status,
        created_at=alert.created_at,
    )


@router.get(
    "/threshold-alerts",
    response_model=ThresholdAlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get threshold alerts",
    description="Retrieve threshold breach alerts with optional filtering by status and severity. "
    "Requires JWT authentication.",
)
async def get_threshold_alerts(
    db: DbDep,
    current_user: CurrentAdminUser,
    status_filter: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> ThresholdAlertListResponse:
    """Retrieve threshold breach alerts.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
    """
    alerts, total_count, unacknowledged_count = await ThresholdAlertService.get_alerts(
        db=db,
        status=status_filter,
        severity=severity,
        limit=limit,
    )
    
    return ThresholdAlertListResponse(
        alerts=[ThresholdAlertResponse.model_validate(alert) for alert in alerts],
        total_count=total_count,
        unacknowledged_count=unacknowledged_count,
    )


@router.get(
    "/threshold-alerts/{alert_id}",
    response_model=ThresholdAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get threshold alert by ID",
    description="Retrieve a single threshold breach alert by ID. "
    "Requires JWT authentication. Returns 404 if not found.",
)
async def get_threshold_alert_by_id(
    alert_id: UUID,
    db: DbDep,
    current_user: CurrentAdminUser,
) -> ThresholdAlertResponse:
    """Retrieve a single threshold alert.
    
    Requirements: 4.9, 4.10
    """
    from app.core.exceptions import NotFoundException
    
    alert = await ThresholdAlertService.get_alert_by_id(db=db, alert_id=alert_id)
    
    if not alert:
        raise NotFoundException(detail=f"Alert with ID {alert_id} not found")
    
    return ThresholdAlertResponse.model_validate(alert)


@router.post(
    "/threshold-alerts/{alert_id}/acknowledge",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge threshold alert",
    description="Acknowledge a threshold breach alert. Updates status to ACKNOWLEDGED "
    "and records the acknowledging admin user. Requires JWT authentication. "
    "Returns 404 if alert not found.",
)
async def acknowledge_threshold_alert(
    alert_id: UUID,
    db: DbDep,
    current_user: CurrentAdminUser,
) -> SuccessResponse:
    """Acknowledge a threshold alert.
    
    Requirements: 5.1, 5.5
    """
    from app.core.exceptions import NotFoundException
    
    success = await ThresholdAlertService.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        admin_id=current_user.user_id,
    )
    
    if not success:
        raise NotFoundException(detail=f"Alert with ID {alert_id} not found")
    
    return SuccessResponse(
        success=True,
        message="Alert acknowledged successfully",
    )


# ============================================================================
# Task 14.1: Risk Analysis Endpoints
# ============================================================================


@router.post(
    "/risk-analysis/request",
    response_model=StatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request risk analysis",
    description="Request risk analysis for a threshold alert. Creates a risk analysis record "
    "with status PENDING and initiates async communication with the Risk Analysis Agent. "
    "Returns 202 Accepted immediately. Use the polling endpoint to check status. "
    "Requires JWT authentication.",
)
async def request_risk_analysis(
    data: RiskAnalysisRequest,
    db: DbDep,
    current_user: CurrentAdminUser,
) -> StatusResponse:
    """Request risk analysis for a threshold alert.
    
    This endpoint initiates an asynchronous risk analysis workflow:
    1. Creates a Risk_Analysis record with status PENDING
    2. Updates the associated alert status to ANALYZING
    3. Sends request to Risk Analysis Agent (async, may take up to 60 seconds)
    4. Returns immediately with 202 Accepted
    
    The frontend should poll GET /api/admin/risk-analysis/{analysis_id} 
    every 2 seconds to check for completion.
    
    Requirements: 6.1, 6.10, 17.7
    """
    # Request risk analysis (async workflow)
    analysis = await RiskAnalysisService.request_analysis(
        db=db,
        alert_id=data.alert_id,
        location=data.location.model_dump(),
        sensor_data=data.sensor_data.model_dump(),
        admin_id=current_user.user_id,
        historical_data=data.historical_data,
    )
    
    return StatusResponse(
        id=analysis.analysis_id,
        status=analysis.status,
        message="Risk analysis request accepted. Poll the analysis endpoint to check status.",
    )


@router.get(
    "/risk-analysis/{analysis_id}",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get risk analysis by ID",
    description="Retrieve a single risk analysis by ID. This is a polling endpoint - "
    "the frontend should call this every 2 seconds until status is COMPLETED or FAILED. "
    "Requires JWT authentication. Returns 404 if not found.",
)
async def get_risk_analysis_by_id(
    analysis_id: UUID,
    db: DbDep,
    current_user: CurrentAdminUser,
) -> RiskAnalysisResponse:
    """Retrieve a single risk analysis.
    
    This is a polling endpoint designed to be called repeatedly to check
    for analysis completion. The status field indicates the current state:
    - PENDING: Analysis in progress, poll again
    - COMPLETED: Analysis finished successfully, all fields populated
    - FAILED: Analysis failed, check analysis_summary for error details
    
    Requirements: 7.1, 7.4, 7.6
    """
    from app.core.exceptions import NotFoundException
    
    analysis = await RiskAnalysisService.get_analysis_by_id(db=db, analysis_id=analysis_id)
    
    if not analysis:
        raise NotFoundException(detail=f"Risk analysis with ID {analysis_id} not found")
    
    return RiskAnalysisResponse.model_validate(analysis)


@router.get(
    "/risk-analysis",
    response_model=RiskAnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all risk analyses",
    description="Retrieve all risk analyses with optional filtering by status. "
    "Supports pagination via limit parameter. Results ordered by created_at descending. "
    "Requires JWT authentication.",
)
async def get_all_risk_analyses(
    db: DbDep,
    current_user: CurrentAdminUser,
    status_filter: str | None = None,
    limit: int = 50,
) -> RiskAnalysisListResponse:
    """Retrieve all risk analyses.
    
    Supports filtering by status (PENDING, COMPLETED, FAILED) and pagination
    via limit parameter. Results are ordered by created_at in descending order
    (most recent first).
    
    Requirements: 7.1, 7.4, 7.6
    """
    analyses, total_count = await RiskAnalysisService.get_all_analyses(
        db=db,
        status=status_filter,
        limit=limit,
    )
    
    return RiskAnalysisListResponse(
        analyses=[RiskAnalysisResponse.model_validate(analysis) for analysis in analyses],
        total_count=total_count,
    )
