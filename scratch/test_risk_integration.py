import asyncio
import uuid
import sys
import logging

# Ensure app is in path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.risk_analysis.service import RiskAnalysisService
from app.modules.risk_analysis.schemas import RiskAnalysisRequest, DisasterKindEnum, ProvinceEnum, BreachSeverityEnum, SourceAPIEnum

# Setup basic logging to see what the service logs
logging.basicConfig(level=logging.INFO)

class MockRepo:
    async def create(self, data):
        print("\n--- DB Persistence Triggered ---")
        print(f"Risk Level saved: {data['risk_level']}")
        print(f"Confidence Score saved: {data['confidence_score']}")
        print(f"Estimated Affected saved: {data['estimated_population_affected']}")
        print("--------------------------------\n")
        return data

async def main():
    repo = MockRepo()
    service = RiskAnalysisService(repo=repo)
    
    req = RiskAnalysisRequest(
        breach_id=str(uuid.uuid4()),
        disaster_kind=DisasterKindEnum.flood,
        location_name="Swat River near Kalam",
        district="Swat",
        province=ProvinceEnum.khyber_pakhtunkhwa,
        latitude=35.48,
        longitude=72.58,
        observed_value=4.5,
        threshold_value=4.0,
        breach_severity=BreachSeverityEnum.warning,
        metric_name="water_level_meters",
        observation_time="2026-05-13T10:00:00Z",
        source_api=SourceAPIEnum.usgs,
        is_forecast_breach=False
    )
    
    print("Initiating assessment request from Main Backend to Risk Analysis Agent...")
    try:
        response = await service.assess(req, user_id=uuid.uuid4())
        print("\n=== SUCCESS: Received Response from Risk Analysis Agent ===")
        print(f"Assessment ID: {response.assessment_id}")
        print(f"Risk Level: {response.risk_level}")
        print(f"Composite Risk Score: {response.composite_risk_score}")
        print(f"Situation Trajectory: {response.situation_trajectory}")
        print(f"Critical Actions Needed: {response.critical_actions_needed}")
        print("===========================================================")
    except Exception as e:
        print(f"\n❌ Error during assessment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
