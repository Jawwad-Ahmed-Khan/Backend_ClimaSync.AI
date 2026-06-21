#!/usr/bin/env python3
"""Quick system status check - minimal dependencies version"""

import sys
import asyncio

async def main():
    print("\n" + "="*70)
    print("ClimaSync Backend - System Status Check".center(70))
    print("="*70 + "\n")
    
    # 1. Test basic imports
    print("1. TESTING CORE IMPORTS...")
    try:
        from app.main import create_app
        print("   ✓ FastAPI app factory imported")
    except Exception as e:
        print(f"   ✗ App import failed: {e}")
        return False
    
    # 2. Test database
    print("\n2. TESTING DATABASE...")
    try:
        from app.core.database import get_engine
        from sqlalchemy import text
        
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("   ✓ Database connection successful")
        print("   ✓ Database pool initialized")
    except Exception as e:
        print(f"   ✗ Database error: {e}")
        return False
    
    # 3. Test WebSocket
    print("\n3. TESTING WEBSOCKETS...")
    try:
        from app.websockets.manager import AdminAlertConnectionManager, admin_ws_manager
        print(f"   ✓ WebSocket manager loaded")
        print(f"   ✓ Active connections: {len(admin_ws_manager.active_admin_connections)}")
    except Exception as e:
        print(f"   ✗ WebSocket error: {e}")
        return False
    
    # 4. Test Incoming Alerts
    print("\n4. TESTING INCOMING ALERTS...")
    try:
        from app.modules.incoming_alerts.service import IncomingAlertService
        from app.modules.incoming_alerts.repository import IncomingAlertRepository
        print("   ✓ Incoming alert service loaded")
        print("   ✓ Incoming alert repository loaded")
    except Exception as e:
        print(f"   ✗ Incoming alerts error: {e}")
        return False
    
    # 5. Test Email Service
    print("\n5. TESTING EMAIL/NOTIFICATION SERVICE...")
    try:
        from app.common.services.notification_service import NotificationService, AIOSMTPLIB_AVAILABLE
        if AIOSMTPLIB_AVAILABLE:
            print("   ✓ aiosmtplib installed - email functional")
        else:
            print("   ⚠ aiosmtplib NOT installed - email logging only")
        print("   ✓ Notification service loaded (gracefully degraded)")
    except Exception as e:
        print(f"   ✗ Notification service error: {e}")
        return False
    
    # 6. Test JWT/Security
    print("\n6. TESTING SECURITY/JWT...")
    try:
        from app.core.security import JOSE_AVAILABLE, hash_password, verify_password
        if JOSE_AVAILABLE:
            print("   ✓ python-jose installed - JWT functional")
        else:
            print("   ⚠ python-jose NOT installed - JWT placeholders only")
        
        # Test password hashing (always works)
        pwd = "test_password_123"
        hashed = hash_password(pwd)
        verified = verify_password(pwd, hashed)
        if verified:
            print("   ✓ Password hashing/verification working")
        else:
            print("   ✗ Password verification failed")
            return False
    except Exception as e:
        print(f"   ✗ Security error: {e}")
        return False
    
    # 7. App Creation
    print("\n7. TESTING APP CREATION...")
    try:
        app = create_app()
        print(f"   ✓ FastAPI app created: {app.title}")
        print(f"   ✓ Total routes: {len(app.routes)}")
    except Exception as e:
        print(f"   ✗ App creation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("✓ System ready! Missing packages are gracefully handled.".center(70))
    print("="*70 + "\n")
    print("NEXT STEPS:")
    print("  1. Install missing packages for full functionality:")
    print("     pip install aiosmtplib python-jose[cryptography]")
    print("\n  2. Start the server:")
    print("     uvicorn main:app --reload")
    print("\n  3. API Docs: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    
    return True

if __name__ == "__main__":
    import os
    os.chdir("c:\\Users\\muhammadtalha.asim\\Downloads\\fyp\\Backend_ClimaSync.AI")
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
