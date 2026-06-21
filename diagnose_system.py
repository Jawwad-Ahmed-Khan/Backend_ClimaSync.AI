#!/usr/bin/env python3
"""Comprehensive diagnostic script for ClimaSync Backend.

Checks:
1. Python environment
2. All dependencies (aiosmtplib, asyncpg, fastapi, etc.)
3. Configuration (DATABASE_URL, SMTP settings, etc.)
4. Module imports
5. Database connectivity
6. WebSocket setup
7. Alert/Email service
"""

import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text: str) -> None:
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def check_mark(msg: str) -> None:
    print(f"{GREEN}✓{RESET} {msg}")

def error_mark(msg: str) -> None:
    print(f"{RED}✗{RESET} {msg}")

def warning_mark(msg: str) -> None:
    print(f"{YELLOW}⚠{RESET} {msg}")

# ============================================================================
# 1. PYTHON ENVIRONMENT
# ============================================================================
def diagnose_python_env() -> bool:
    print_header("1. PYTHON ENVIRONMENT")
    success = True
    
    check_mark(f"Python version: {sys.version.split()[0]}")
    check_mark(f"Executable: {sys.executable}")
    
    if sys.version_info < (3, 12):
        error_mark("Python 3.12+ is required")
        success = False
    else:
        check_mark(f"Python 3.12+ requirement met")
    
    return success

# ============================================================================
# 2. DEPENDENCIES
# ============================================================================
def diagnose_dependencies() -> bool:
    print_header("2. REQUIRED DEPENDENCIES")
    
    required_packages = {
        "aiosmtplib": "Email sending (SMTP)",
        "asyncpg": "PostgreSQL async driver",
        "fastapi": "Web framework",
        "pydantic": "Data validation",
        "pydantic_settings": "Configuration management",
        "sqlalchemy": "ORM",
        "uvicorn": "ASGI server",
        "email_validator": "Email validation",
        "python_jose": "JWT tokens",
        "passlib": "Password hashing",
        "slowapi": "Rate limiting",
    }
    
    missing = []
    for pkg, description in required_packages.items():
        try:
            __import__(pkg.replace("-", "_"))
            check_mark(f"{pkg:<20} - {description}")
        except ImportError:
            error_mark(f"{pkg:<20} - {description}")
            missing.append(pkg)
    
    if missing:
        print(f"\n{RED}Missing packages:{RESET}")
        for pkg in missing:
            print(f"  - {pkg}")
        return False
    
    return True

# ============================================================================
# 3. CONFIGURATION
# ============================================================================
def diagnose_configuration() -> bool:
    print_header("3. CONFIGURATION")
    
    try:
        from app.core.config import settings
        
        check_mark(f"App Name: {settings.APP_NAME}")
        check_mark(f"App Version: {settings.APP_VERSION}")
        check_mark(f"Environment: {settings.ENVIRONMENT}")
        check_mark(f"API V1 Prefix: {settings.API_V1_PREFIX}")
        
        # Database
        if settings.DATABASE_URL:
            check_mark(f"Database URL configured: {settings.DATABASE_URL[:30]}...")
        else:
            error_mark("DATABASE_URL not set!")
            return False
        
        # SMTP
        print(f"\n{BLUE}SMTP Configuration:{RESET}")
        if settings.SMTP_HOST:
            check_mark(f"SMTP Host: {settings.SMTP_HOST}")
        else:
            warning_mark("SMTP_HOST not configured")
        
        if settings.SMTP_PORT:
            check_mark(f"SMTP Port: {settings.SMTP_PORT}")
        else:
            warning_mark("SMTP_PORT not set")
        
        if settings.SMTP_USERNAME:
            check_mark(f"SMTP Username: {settings.SMTP_USERNAME[:5]}...")
        else:
            warning_mark("SMTP_USERNAME not set (email won't work)")
        
        if settings.SMTP_FROM_EMAIL:
            check_mark(f"SMTP From Email: {settings.SMTP_FROM_EMAIL}")
        else:
            warning_mark("SMTP_FROM_EMAIL not set")
        
        # Modules
        print(f"\n{BLUE}Module Kill Switches:{RESET}")
        modules = {
            "MODULE_AUTH_ENABLED": "Auth",
            "MODULE_ADMIN_ENABLED": "Admin",
            "MODULE_TASKS_ENABLED": "Tasks",
            "MODULE_DISASTERS_ENABLED": "Disasters",
            "MODULE_RESOURCES_ENABLED": "Resources",
            "MODULE_SOCIAL_ENABLED": "Social",
            "MODULE_INCOMING_ALERTS_ENABLED": "Incoming Alerts",
        }
        
        for attr, name in modules.items():
            status = "✓ Enabled" if getattr(settings, attr) else "✗ Disabled"
            print(f"  {name:<20} {status}")
        
        return True
    
    except Exception as e:
        error_mark(f"Configuration error: {e}")
        return False

# ============================================================================
# 4. MODULE IMPORTS
# ============================================================================
def diagnose_module_imports() -> bool:
    print_header("4. MODULE IMPORTS")
    
    modules_to_check = [
        "app.main",
        "app.core.config",
        "app.core.database",
        "app.core.security",
        "app.websockets.manager",
        "app.modules.incoming_alerts.service",
        "app.modules.incoming_alerts.controller",
        "app.modules.auth.service",
        "app.common.services.notification_service",
    ]
    
    failed = []
    for module_path in modules_to_check:
        try:
            __import__(module_path)
            check_mark(f"{module_path}")
        except Exception as e:
            error_mark(f"{module_path}: {e}")
            failed.append((module_path, e))
    
    if failed:
        print(f"\n{RED}Failed imports:{RESET}")
        for path, err in failed:
            print(f"  {path}: {err}")
        return False
    
    return True

# ============================================================================
# 5. DATABASE CONNECTIVITY
# ============================================================================
async def diagnose_database() -> bool:
    print_header("5. DATABASE CONNECTIVITY")
    
    try:
        from app.core.database import get_engine
        from sqlalchemy import text
        
        engine = get_engine()
        check_mark("Engine created successfully")
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                check_mark("Database query successful (SELECT 1)")
            else:
                error_mark("Database returned unexpected result")
                return False
        
        check_mark("Database connection pool healthy")
        return True
    
    except Exception as e:
        error_mark(f"Database connection failed: {e}")
        return False

# ============================================================================
# 6. WEBSOCKET SETUP
# ============================================================================
def diagnose_websocket_setup() -> bool:
    print_header("6. WEBSOCKET SETUP")
    
    try:
        from app.websockets.manager import AdminAlertConnectionManager, admin_ws_manager
        
        check_mark("AdminAlertConnectionManager imported")
        check_mark(f"Singleton instance created: {admin_ws_manager}")
        check_mark(f"Active connections tracking: {len(admin_ws_manager.active_admin_connections)} (should be 0 at startup)")
        
        # Check methods exist
        required_methods = ["connect", "disconnect", "broadcast_alert"]
        for method in required_methods:
            if hasattr(admin_ws_manager, method):
                check_mark(f"Method '{method}' available")
            else:
                error_mark(f"Method '{method}' missing!")
                return False
        
        return True
    
    except Exception as e:
        error_mark(f"WebSocket setup error: {e}")
        return False

# ============================================================================
# 7. ALERT/EMAIL SERVICE
# ============================================================================
async def diagnose_alert_service() -> bool:
    print_header("7. ALERT & EMAIL SERVICE")
    
    try:
        from app.common.services.notification_service import NotificationService
        from app.core.config import settings
        
        check_mark("NotificationService imported")
        
        # Check methods
        required_methods = [
            "dispatch_platform_alert",
            "dispatch_otp_verification",
            "dispatch_password_recovery",
        ]
        
        for method in required_methods:
            if hasattr(NotificationService, method):
                check_mark(f"Method '{method}' available")
            else:
                error_mark(f"Method '{method}' missing!")
                return False
        
        # Check SMTP config
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            warning_mark("SMTP credentials not configured - email sending will fail")
            warning_mark("Set SMTP_USERNAME and SMTP_PASSWORD in .env")
            return True  # Not a hard failure, just warning
        else:
            check_mark("SMTP credentials configured")
        
        return True
    
    except Exception as e:
        error_mark(f"Alert/Email service error: {e}")
        return False

# ============================================================================
# 8. INCOMING ALERTS MODULE
# ============================================================================
def diagnose_incoming_alerts() -> bool:
    print_header("8. INCOMING ALERTS MODULE")
    
    try:
        from app.modules.incoming_alerts.service import IncomingAlertService
        from app.modules.incoming_alerts.repository import IncomingAlertRepository
        from app.modules.incoming_alerts.schemas import IncomingBreachPayload
        from app.modules.incoming_alerts.controller import router, ws_router
        
        check_mark("IncomingAlertService imported")
        check_mark("IncomingAlertRepository imported")
        check_mark("IncomingBreachPayload schema imported")
        check_mark("REST router imported")
        check_mark("WebSocket router imported")
        
        # Check required attributes
        if hasattr(router, "routes") or hasattr(router, "dependency_cache"):
            check_mark("REST router has routes")
        
        if hasattr(ws_router, "routes") or hasattr(ws_router, "dependency_cache"):
            check_mark("WebSocket router has routes")
        
        return True
    
    except Exception as e:
        error_mark(f"Incoming alerts module error: {e}")
        return False

# ============================================================================
# 9. APP CREATION
# ============================================================================
def diagnose_app_creation() -> bool:
    print_header("9. FASTAPI APP CREATION")
    
    try:
        from app.main import create_app
        
        app = create_app()
        check_mark("FastAPI app created successfully")
        check_mark(f"App title: {app.title}")
        check_mark(f"App version: {app.version}")
        
        # Check routers
        if hasattr(app, "routes"):
            num_routes = len(app.routes)
            check_mark(f"Total routes: {num_routes}")
            
            # Sample of routes
            rest_routes = [r for r in app.routes if hasattr(r, "path")]
            for route in rest_routes[:5]:
                print(f"  - {route.path}")
        
        return True
    
    except Exception as e:
        error_mark(f"App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN DIAGNOSTIC
# ============================================================================
async def main() -> None:
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'ClimaSync Backend Diagnostic Report':^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {}
    
    # Synchronous checks
    results["Python Environment"] = diagnose_python_env()
    results["Dependencies"] = diagnose_dependencies()
    results["Configuration"] = diagnose_configuration()
    results["Module Imports"] = diagnose_module_imports()
    results["WebSocket Setup"] = diagnose_websocket_setup()
    results["Incoming Alerts"] = diagnose_incoming_alerts()
    results["App Creation"] = diagnose_app_creation()
    
    # Async checks
    results["Database Connectivity"] = await diagnose_database()
    results["Alert/Email Service"] = await diagnose_alert_service()
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status:20} {name}")
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    if passed == total:
        print(f"{GREEN}All checks passed! ({passed}/{total}){RESET}")
    else:
        print(f"{YELLOW}Some issues found ({passed}/{total} passed){RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
