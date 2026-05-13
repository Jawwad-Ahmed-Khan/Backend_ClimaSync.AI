"""Business logic services for disaster management workflow.

This module implements the service layer for:
- Admin authentication (account creation, login)
- Threshold alert management
- Risk analysis workflow orchestration
- Precautionary measures workflow orchestration

Services coordinate between repositories, agent clients, and external systems.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, UnauthorizedException, ForbiddenException
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.modules.admin_workflow.models import AdminUser

logger = logging.getLogger(__name__)


# ============================================================================
# Task 5.1: AdminAuthService
# ============================================================================


class AdminAuthService:
    """Service for admin account management and authentication.
    
    Handles:
    - Admin account creation with password hashing
    - Admin authentication with password verification
    - JWT token generation
    """

    @staticmethod
    async def create_admin(
        db: Session,
        email: str,
        password: str,
        org_name: str,
        full_name: str,
    ) -> AdminUser:
        """Create a new admin account.
        
        Args:
            db: Database session
            email: Admin email address (must be unique)
            password: Plain-text password (will be hashed with bcrypt)
            org_name: Organization name
            full_name: Admin's full name
            
        Returns:
            Created AdminUser instance
            
        Raises:
            BadRequestException: If email already exists
            
        Requirements: 1.1, 1.2, 1.4
        """
        # Hash password using bcrypt (from app/core/security.py)
        password_hash = hash_password(password)
        
        # Create admin user
        admin = AdminUser(
            email=email,
            password_hash=password_hash,
            org_name=org_name,
            full_name=full_name,
            role="admin",
            is_active=True,
        )
        
        try:
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            logger.info(
                "Admin account created",
                extra={
                    "user_id": str(admin.user_id),
                    "email": admin.email,
                    "org_name": admin.org_name,
                },
            )
            
            return admin
            
        except IntegrityError as e:
            db.rollback()
            logger.warning(
                "Admin account creation failed - duplicate email",
                extra={
                    "email": email,
                    "error": str(e),
                },
            )
            raise BadRequestException(
                detail=f"An account with email '{email}' already exists"
            )

    @staticmethod
    async def authenticate_admin(
        db: Session,
        email: str,
        password: str,
    ) -> AdminUser:
        """Authenticate an admin user.
        
        Args:
            db: Database session
            email: Admin email address
            password: Plain-text password
            
        Returns:
            Authenticated AdminUser instance
            
        Raises:
            UnauthorizedException: If credentials are invalid
            ForbiddenException: If account is inactive
            
        Requirements: 2.1, 2.2, 2.4, 2.5
        """
        # Query admin by email
        admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        
        # Check if admin exists and password is correct
        if not admin or not verify_password(password, admin.password_hash):
            logger.warning(
                "Admin login failed - invalid credentials",
                extra={
                    "email": email,
                    "reason": "invalid_credentials",
                },
            )
            raise UnauthorizedException(detail="Invalid email or password")
        
        # Check if account is active
        if not admin.is_active:
            logger.warning(
                "Admin login failed - inactive account",
                extra={
                    "email": email,
                    "user_id": str(admin.user_id),
                    "reason": "inactive_account",
                },
            )
            raise ForbiddenException(detail="Account is disabled")
        
        logger.info(
            "Admin login successful",
            extra={
                "user_id": str(admin.user_id),
                "email": admin.email,
            },
        )
        
        return admin



# ============================================================================
# Task 8.1: ThresholdAlertService
# ============================================================================


class ThresholdAlertService:
    """Service for threshold alert management.
    
    Handles:
    - Alert creation with status NEW
    - Alert retrieval with filtering and ordering
    - Alert acknowledgment
    """

    @staticmethod
    async def create_alert(
        db: Session,
        data: dict,
    ) -> "ThresholdBreachAlert":
        """Create a new threshold breach alert.
        
        Args:
            db: Database session
            data: Alert data dictionary
            
        Returns:
            Created ThresholdBreachAlert instance
            
        Requirements: 3.4, 3.10, 13.6
        """
        from app.modules.admin_workflow.models import ThresholdBreachAlert
        
        # Create alert with status NEW
        alert = ThresholdBreachAlert(
            sensor_type=data.get("sensor_type", "unknown"),
            latitude=data["latitude"],
            longitude=data["longitude"],
            location_name=data.get("location_name", "Unknown"),
            province=data.get("province", "Unknown"),
            current_value=data["current_value"],
            threshold_value=data["threshold_value"],
            breach_percentage=data.get("breach_percentage", 0.0),
            severity=data["severity"],
            data_source=data.get("data_source", "unknown"),
            status="NEW",
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(
            "Threshold alert created",
            extra={
                "alert_id": str(alert.alert_id),
                "severity": alert.severity,
                "sensor_type": alert.sensor_type,
                "location": alert.location_name,
            },
        )
        
        return alert

    @staticmethod
    async def get_alerts(
        db: Session,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> tuple[list["ThresholdBreachAlert"], int, int]:
        """Retrieve threshold alerts with filtering.
        
        Args:
            db: Database session
            status: Optional status filter
            severity: Optional severity filter
            limit: Maximum number of alerts to return (default 50)
            
        Returns:
            Tuple of (alerts list, total_count, unacknowledged_count)
            
        Requirements: 4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
        """
        from app.modules.admin_workflow.models import ThresholdBreachAlert
        
        # Build query with filters
        query = db.query(ThresholdBreachAlert)
        
        if status:
            query = query.filter(ThresholdBreachAlert.status == status)
        
        if severity:
            query = query.filter(ThresholdBreachAlert.severity == severity)
        
        # Get total count
        total_count = query.count()
        
        # Get unacknowledged count (status = NEW)
        unacknowledged_count = db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.status == "NEW"
        ).count()
        
        # Order by created_at DESC and apply limit
        alerts = query.order_by(ThresholdBreachAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total_count, unacknowledged_count

    @staticmethod
    async def get_alert_by_id(
        db: Session,
        alert_id: UUID,
    ) -> "ThresholdBreachAlert | None":
        """Retrieve a single threshold alert by ID.
        
        Args:
            db: Database session
            alert_id: Alert UUID
            
        Returns:
            ThresholdBreachAlert instance or None if not found
            
        Requirements: 4.9, 4.10
        """
        from app.modules.admin_workflow.models import ThresholdBreachAlert
        
        return db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.alert_id == alert_id
        ).first()

    @staticmethod
    async def acknowledge_alert(
        db: Session,
        alert_id: UUID,
        admin_id: UUID,
    ) -> bool:
        """Acknowledge a threshold alert.
        
        Args:
            db: Database session
            alert_id: Alert UUID
            admin_id: Admin user UUID
            
        Returns:
            True if successful, False if alert not found
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.6
        """
        from app.modules.admin_workflow.models import ThresholdBreachAlert
        
        alert = db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.alert_id == alert_id
        ).first()
        
        if not alert:
            return False
        
        # Update status to ACKNOWLEDGED
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = admin_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(
            "Threshold alert acknowledged",
            extra={
                "alert_id": str(alert_id),
                "admin_id": str(admin_id),
            },
        )
        
        return True



# ============================================================================
# Task 13.1: RiskAnalysisService
# ============================================================================


class RiskAnalysisService:
    """Service for risk analysis workflow orchestration.
    
    Handles:
    - Risk analysis request workflow (create PENDING, call agent, update status)
    - Risk analysis retrieval with filtering
    - Async agent communication with error handling
    """

    @staticmethod
    async def request_analysis(
        db: Session,
        alert_id: UUID,
        location: dict,
        sensor_data: dict,
        admin_id: UUID,
        historical_data: dict | None = None,
    ) -> "RiskAnalysis":
        """Request risk analysis for a threshold alert.
        
        Workflow:
        1. Create Risk_Analysis record with status PENDING
        2. Update associated alert status to ANALYZING
        3. Send async request to Risk_Analysis_Agent via agent_client
        4. On success: update analysis with result, set status COMPLETED, set completed_at
        5. On failure: update analysis with error message, set status FAILED
        
        Args:
            db: Database session
            alert_id: UUID of the threshold alert
            location: Location data dict (latitude, longitude, location_name, province)
            sensor_data: Sensor data dict (sensor_type, current_value, threshold_value)
            admin_id: Admin user UUID requesting the analysis
            historical_data: Optional historical data for context
            
        Returns:
            RiskAnalysis instance (status may be PENDING, COMPLETED, or FAILED)
            
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.7, 6.8, 6.9, 6.10, 13.7
        """
        from app.modules.admin_workflow.models import RiskAnalysis, ThresholdBreachAlert
        from app.modules.admin_workflow.agent_client import agent_client
        
        # 1. Create Risk_Analysis record with status PENDING
        analysis = RiskAnalysis(
            alert_id=alert_id,
            risk_score=0,  # Placeholder, will be updated by agent
            risk_level="PENDING",  # Placeholder
            disaster_type="UNKNOWN",  # Placeholder
            affected_area_km2=0.0,  # Placeholder
            estimated_population_affected=0,  # Placeholder
            confidence_score=0,  # Placeholder
            analysis_summary="Analysis in progress...",
            detailed_analysis={},  # Placeholder
            recommended_actions={},  # Placeholder
            status="PENDING",
            requested_by=admin_id,
            requested_at=datetime.now(timezone.utc),
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        logger.info(
            "Risk analysis created with status PENDING",
            extra={
                "analysis_id": str(analysis.analysis_id),
                "alert_id": str(alert_id),
                "admin_id": str(admin_id),
                "status": "PENDING",
            },
        )
        
        # 2. Update associated alert status to ANALYZING
        alert = db.query(ThresholdBreachAlert).filter(
            ThresholdBreachAlert.alert_id == alert_id
        ).first()
        
        if alert:
            alert.status = "ANALYZING"
            db.commit()
            
            logger.info(
                "Alert status updated to ANALYZING",
                extra={
                    "alert_id": str(alert_id),
                    "analysis_id": str(analysis.analysis_id),
                },
            )
        
        # 3. Send async request to Risk_Analysis_Agent via agent_client
        try:
            # Prepare request data for agent
            agent_request_data = {
                "alert_id": str(alert_id),
                "location": location,
                "sensor_data": sensor_data,
                "historical_data": historical_data,
            }
            
            logger.info(
                "Sending risk analysis request to agent",
                extra={
                    "analysis_id": str(analysis.analysis_id),
                    "alert_id": str(alert_id),
                },
            )
            
            # Call agent (this is async and may take up to 60 seconds)
            result = await agent_client.request_risk_analysis(agent_request_data)
            
            # 4. On success: update analysis with result, set status COMPLETED, set completed_at
            analysis.risk_score = result.get("risk_score", 0)
            analysis.risk_level = result.get("risk_level", "UNKNOWN")
            analysis.disaster_type = result.get("disaster_type", "UNKNOWN")
            analysis.affected_area_km2 = result.get("affected_area_km2", 0.0)
            analysis.estimated_population_affected = result.get("estimated_population_affected", 0)
            analysis.confidence_score = result.get("confidence_score", 0)
            analysis.analysis_summary = result.get("analysis_summary", "")
            analysis.detailed_analysis = result.get("detailed_analysis", {})
            analysis.recommended_actions = result.get("recommended_actions", {})
            analysis.status = "COMPLETED"
            analysis.completed_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(analysis)
            
            logger.info(
                "Risk analysis completed successfully",
                extra={
                    "analysis_id": str(analysis.analysis_id),
                    "alert_id": str(alert_id),
                    "status": "COMPLETED",
                    "risk_level": analysis.risk_level,
                    "disaster_type": analysis.disaster_type,
                },
            )
            
        except Exception as e:
            # 5. On failure: update analysis with error message, set status FAILED
            analysis.status = "FAILED"
            analysis.analysis_summary = f"Risk analysis failed: {str(e)}"
            analysis.completed_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(analysis)
            
            logger.error(
                "Risk analysis failed",
                extra={
                    "analysis_id": str(analysis.analysis_id),
                    "alert_id": str(alert_id),
                    "status": "FAILED",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
        
        return analysis

    @staticmethod
    async def get_analysis_by_id(
        db: Session,
        analysis_id: UUID,
    ) -> "RiskAnalysis | None":
        """Retrieve a single risk analysis by ID.
        
        Args:
            db: Database session
            analysis_id: Analysis UUID
            
        Returns:
            RiskAnalysis instance or None if not found
            
        Requirements: 7.1, 7.2, 7.3, 7.6
        """
        from app.modules.admin_workflow.models import RiskAnalysis
        
        return db.query(RiskAnalysis).filter(
            RiskAnalysis.analysis_id == analysis_id
        ).first()

    @staticmethod
    async def get_all_analyses(
        db: Session,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[list["RiskAnalysis"], int]:
        """Retrieve all risk analyses with optional filtering.
        
        Args:
            db: Database session
            status: Optional status filter (PENDING, COMPLETED, FAILED)
            limit: Maximum number of analyses to return (default 50)
            
        Returns:
            Tuple of (analyses list, total_count)
            
        Requirements: 7.4, 7.5
        """
        from app.modules.admin_workflow.models import RiskAnalysis
        
        # Build query with filters
        query = db.query(RiskAnalysis)
        
        if status:
            query = query.filter(RiskAnalysis.status == status)
        
        # Get total count
        total_count = query.count()
        
        # Order by created_at DESC and apply limit
        analyses = query.order_by(RiskAnalysis.created_at.desc()).limit(limit).all()
        
        return analyses, total_count



# ============================================================================
# Task 16.1: PrecautionaryService
# ============================================================================


class PrecautionaryService:
    """Service for precautionary measures workflow orchestration.
    
    Handles:
    - Precautionary measures request workflow (create PENDING, call agent, update status)
    - Precautionary measures retrieval with filtering
    - Precautionary measures approval
    - Async agent communication with error handling
    """

    @staticmethod
    async def request_measures(
        db: Session,
        analysis_id: UUID,
        risk_analysis_data: dict,
        location: dict,
        admin_id: UUID,
    ) -> "PrecautionaryMeasure":
        """Request precautionary measures for a risk analysis.
        
        Workflow:
        1. Create Precautionary_Measure record with status PENDING
        2. Send async request to Precautionary_Agent via agent_client
        3. On success: update precaution with result, set status GENERATED, set generated_at
        4. On failure: update precaution with error message, set status FAILED
        
        Args:
            db: Database session
            analysis_id: UUID of the risk analysis
            risk_analysis_data: Risk analysis data dict (risk_score, risk_level, disaster_type, etc.)
            location: Location data dict (latitude, longitude, location_name, province)
            admin_id: Admin user UUID requesting the measures
            
        Returns:
            PrecautionaryMeasure instance (status may be PENDING, GENERATED, or FAILED)
            
        Requirements: 8.1, 8.2, 8.3, 8.6, 8.7, 8.8, 8.9, 13.8
        """
        from app.modules.admin_workflow.models import PrecautionaryMeasure
        from app.modules.admin_workflow.agent_client import agent_client
        
        # 1. Create Precautionary_Measure record with status PENDING
        precaution = PrecautionaryMeasure(
            analysis_id=analysis_id,
            disaster_type=risk_analysis_data.get("disaster_type", "UNKNOWN"),
            risk_level=risk_analysis_data.get("risk_level", "UNKNOWN"),
            overall_strategy="Measures generation in progress...",
            measures={},  # Placeholder, will be updated by agent
            timeline={},  # Placeholder, will be updated by agent
            estimated_cost=None,
            status="PENDING",
            requested_by=admin_id,
            requested_at=datetime.now(timezone.utc),
        )
        
        db.add(precaution)
        db.commit()
        db.refresh(precaution)
        
        logger.info(
            "Precautionary measures created with status PENDING",
            extra={
                "precaution_id": str(precaution.precaution_id),
                "analysis_id": str(analysis_id),
                "admin_id": str(admin_id),
                "status": "PENDING",
                "disaster_type": precaution.disaster_type,
            },
        )
        
        # 2. Send async request to Precautionary_Agent via agent_client
        try:
            # Prepare request data for agent
            agent_request_data = {
                "analysis_id": str(analysis_id),
                "risk_analysis_data": risk_analysis_data,
                "location": location,
            }
            
            logger.info(
                "Sending precautionary measures request to agent",
                extra={
                    "precaution_id": str(precaution.precaution_id),
                    "analysis_id": str(analysis_id),
                },
            )
            
            # Call agent (this is async and may take up to 60 seconds)
            result = await agent_client.request_precautionary_measures(agent_request_data)
            
            # 3. On success: update precaution with result, set status GENERATED, set generated_at
            precaution.overall_strategy = result.get("overall_strategy", "")
            precaution.measures = result.get("measures", {})
            precaution.timeline = result.get("timeline", {})
            precaution.estimated_cost = result.get("estimated_cost")
            precaution.status = "GENERATED"
            precaution.generated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(precaution)
            
            logger.info(
                "Precautionary measures generated successfully",
                extra={
                    "precaution_id": str(precaution.precaution_id),
                    "analysis_id": str(analysis_id),
                    "status": "GENERATED",
                    "disaster_type": precaution.disaster_type,
                    "measures_count": len(result.get("measures", [])),
                },
            )
            
        except Exception as e:
            # 4. On failure: update precaution with error message, set status FAILED
            precaution.status = "FAILED"
            precaution.overall_strategy = f"Precautionary measures generation failed: {str(e)}"
            precaution.generated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(precaution)
            
            logger.error(
                "Precautionary measures generation failed",
                extra={
                    "precaution_id": str(precaution.precaution_id),
                    "analysis_id": str(analysis_id),
                    "status": "FAILED",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
        
        return precaution

    @staticmethod
    async def get_measures_by_id(
        db: Session,
        precaution_id: UUID,
    ) -> "PrecautionaryMeasure | None":
        """Retrieve a single precautionary measure by ID.
        
        Args:
            db: Database session
            precaution_id: Precaution UUID
            
        Returns:
            PrecautionaryMeasure instance or None if not found
            
        Requirements: 9.1, 9.2, 9.3, 9.6
        """
        from app.modules.admin_workflow.models import PrecautionaryMeasure
        
        return db.query(PrecautionaryMeasure).filter(
            PrecautionaryMeasure.precaution_id == precaution_id
        ).first()

    @staticmethod
    async def get_all_measures(
        db: Session,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[list["PrecautionaryMeasure"], int]:
        """Retrieve all precautionary measures with optional filtering.
        
        Args:
            db: Database session
            status: Optional status filter (PENDING, GENERATED, APPROVED, IMPLEMENTED)
            limit: Maximum number of measures to return (default 50)
            
        Returns:
            Tuple of (measures list, total_count)
            
        Requirements: 9.4, 9.5
        """
        from app.modules.admin_workflow.models import PrecautionaryMeasure
        
        # Build query with filters
        query = db.query(PrecautionaryMeasure)
        
        if status:
            query = query.filter(PrecautionaryMeasure.status == status)
        
        # Get total count
        total_count = query.count()
        
        # Order by created_at DESC and apply limit
        measures = query.order_by(PrecautionaryMeasure.created_at.desc()).limit(limit).all()
        
        return measures, total_count

    @staticmethod
    async def approve_measures(
        db: Session,
        precaution_id: UUID,
        admin_id: UUID,
    ) -> bool:
        """Approve precautionary measures.
        
        Args:
            db: Database session
            precaution_id: Precaution UUID
            admin_id: Admin user UUID approving the measures
            
        Returns:
            True if successful, False if precaution not found
            
        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        """
        from app.modules.admin_workflow.models import PrecautionaryMeasure
        
        precaution = db.query(PrecautionaryMeasure).filter(
            PrecautionaryMeasure.precaution_id == precaution_id
        ).first()
        
        if not precaution:
            return False
        
        # Update status to APPROVED
        precaution.status = "APPROVED"
        precaution.approved_by = admin_id
        precaution.approved_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info(
            "Precautionary measures approved",
            extra={
                "precaution_id": str(precaution_id),
                "admin_id": str(admin_id),
                "disaster_type": precaution.disaster_type,
            },
        )
        
        return True
