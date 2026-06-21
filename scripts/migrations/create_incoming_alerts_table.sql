-- Migration: Create incoming_alerts table
-- Run this against the main PostgreSQL database before starting the server.

CREATE TABLE IF NOT EXISTS incoming_alerts (
    breach_id           VARCHAR(36)              NOT NULL,
    source_api          VARCHAR(50)              NOT NULL,
    disaster_kind       VARCHAR(50)              NOT NULL,
    location_name       VARCHAR(255),
    district            VARCHAR(100),
    province            VARCHAR(100),
    latitude            DOUBLE PRECISION         NOT NULL,
    longitude           DOUBLE PRECISION         NOT NULL,
    metric_name         VARCHAR(100)             NOT NULL,
    observed_value      DOUBLE PRECISION         NOT NULL,
    threshold_value     DOUBLE PRECISION         NOT NULL,
    unit                VARCHAR(50)              NOT NULL,
    breach_severity     VARCHAR(20)              NOT NULL,
    observation_time    TIMESTAMPTZ              NOT NULL,
    detected_at         TIMESTAMPTZ              NOT NULL,
    is_forecast         BOOLEAN                  NOT NULL DEFAULT FALSE,
    forecast_horizon_h  INTEGER,
    seismic_event_id    VARCHAR(100),
    weather_location_id VARCHAR(200),
    gauge_id            VARCHAR(200),
    received_at         TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ              NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_incoming_alerts PRIMARY KEY (breach_id)
);

-- Index to quickly filter by source and severity
CREATE INDEX IF NOT EXISTS idx_incoming_alerts_source_api   ON incoming_alerts (source_api);
CREATE INDEX IF NOT EXISTS idx_incoming_alerts_severity     ON incoming_alerts (breach_severity);
CREATE INDEX IF NOT EXISTS idx_incoming_alerts_received_at  ON incoming_alerts (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_incoming_alerts_disaster_kind ON incoming_alerts (disaster_kind);

COMMENT ON TABLE incoming_alerts IS
    'Raw breach payloads received from the Data Collection Service microservice. '
    'One row per unique breach_id. Serves as an audit log and replay source.';
