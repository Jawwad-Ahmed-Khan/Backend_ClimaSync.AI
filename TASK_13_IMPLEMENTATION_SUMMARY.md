# Task 13 Implementation Summary: Risk Analysis Service

## Overview
Successfully implemented the `RiskAnalysisService` class in `app/modules/admin_workflow/services.py` as specified in Task 13.1.

## Implementation Details

### Class: RiskAnalysisService

The service implements three core methods for risk analysis workflow orchestration:

#### 1. `request_analysis()` - Main Workflow Method

**Workflow Steps:**
1. **Create PENDING Record**: Creates a `RiskAnalysis` record with status `PENDING` and placeholder values
2. **Update Alert Status**: Updates the associated `ThresholdBreachAlert` status to `ANALYZING`
3. **Call Agent**: Sends async request to Risk_Analysis_Agent via `agent_client.request_risk_analysis()`
4. **On Success**: 
   - Updates analysis with all result fields (risk_score, risk_level, disaster_type, etc.)
   - Sets status to `COMPLETED`
   - Records `completed_at` timestamp
5. **On Failure**:
   - Sets status to `FAILED`
   - Records error message in `analysis_summary`
   - Records `completed_at` timestamp

**Parameters:**
- `db`: Database session
- `alert_id`: UUID of the threshold alert
- `location`: Location data dict (latitude, longitude, location_name, province)
- `sensor_data`: Sensor data dict (sensor_type, current_value, threshold_value)
- `admin_id`: Admin user UUID requesting the analysis
- `historical_data`: Optional historical data for context

**Returns:** `RiskAnalysis` instance (status may be PENDING, COMPLETED, or FAILED)

**Logging:**
- Logs analysis creation with PENDING status
- Logs alert status update to ANALYZING
- Logs agent request initiation
- Logs successful completion with risk_level and disaster_type
- Logs failures with error details and error type

#### 2. `get_analysis_by_id()` - Single Analysis Retrieval

**Purpose:** Retrieve a single risk analysis by its UUID

**Parameters:**
- `db`: Database session
- `analysis_id`: Analysis UUID

**Returns:** `RiskAnalysis` instance or `None` if not found

#### 3. `get_all_analyses()` - List Analyses with Filtering

**Purpose:** Retrieve all risk analyses with optional status filtering and pagination

**Parameters:**
- `db`: Database session
- `status`: Optional status filter (PENDING, COMPLETED, FAILED)
- `limit`: Maximum number of analyses to return (default 50)

**Returns:** Tuple of `(analyses list, total_count)`

**Features:**
- Filters by status if provided
- Orders by `created_at` DESC (most recent first)
- Applies limit for pagination
- Returns total count for UI pagination

## Requirements Satisfied

The implementation satisfies the following requirements:

- **6.1**: Create Risk_Analysis record with status PENDING
- **6.2**: Update associated alert status to ANALYZING
- **6.3**: Send async request to Risk_Analysis_Agent
- **6.4**: Include alert_id, location, sensor_data, and optional historical_data in request
- **6.7**: Update Risk_Analysis record with all result fields on success
- **6.8**: Update status to COMPLETED and record completed_at timestamp
- **6.9**: Update status to FAILED and record error message on failure
- **6.10**: Return 202 Accepted with analysis_id and status PENDING (handled by controller)
- **7.1**: Provide polling endpoint to retrieve Risk_Analysis by analysis_id
- **7.2**: Return current status (PENDING, COMPLETED, or FAILED)
- **7.3**: Return all analysis data when status is COMPLETED
- **7.4**: Provide endpoint to retrieve all Risk_Analysis records with status filtering
- **7.5**: Order Risk_Analysis records by created_at DESC
- **7.6**: Return 404 when analysis_id does not exist (handled by controller)
- **13.7**: Add structured logging for all state transitions

## Error Handling

The implementation includes comprehensive error handling:

1. **Agent Communication Errors**: All exceptions from `agent_client` are caught and logged
2. **Status Updates**: Failed analyses are marked with status `FAILED` and error details
3. **Structured Logging**: All state transitions include contextual information (analysis_id, alert_id, status, error details)
4. **Database Transactions**: Proper commit/refresh patterns ensure data consistency

## Integration Points

The service integrates with:

1. **Models**: `RiskAnalysis`, `ThresholdBreachAlert` from `app.modules.admin_workflow.models`
2. **Agent Client**: `agent_client` from `app.modules.admin_workflow.agent_client`
3. **Database**: SQLAlchemy Session for all database operations
4. **Logging**: Python logging with structured extra fields

## Next Steps

The controller layer (Task 14.1) will use this service to implement the following endpoints:
- `POST /api/admin/risk-analysis/request` - Request new analysis
- `GET /api/admin/risk-analysis/{analysis_id}` - Poll analysis status
- `GET /api/admin/risk-analysis` - List all analyses with filtering

## Testing Considerations

For future testing:
1. Mock `agent_client.request_risk_analysis()` to test success/failure paths
2. Verify status transitions (NEW → ANALYZING → COMPLETED/FAILED)
3. Test filtering and ordering in `get_all_analyses()`
4. Verify structured logging output
5. Test error handling for agent timeouts and HTTP errors
