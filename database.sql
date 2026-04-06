-- ============================================================================
-- CLIMASYNC AI — FINAL POLISHED DATABASE SCHEMA
-- ============================================================================
-- Environment  : Supabase SQL Editor
-- Scope        : Admin + NGO (Volunteer/Public = future scope)
-- Auth         : Custom (JWT + Refresh Tokens + OTP)
-- Tables       : 18
-- Views        : 8
-- Enums        : 15
-- ============================================================================
-- RESOLVED ISSUES:
--   C1  Partial unique index on users.email (soft-delete safe)
--   C2  UNIQUE(ngo_id, specialization) on ngo_specializations
--   C3  UNIQUE(ngo_id, province, district) on ngo_operational_areas
--   I1  alert_source enum expanded + source_name column
--   I2  'false_alarm' added to alert_status
--   I3  'landslide' kept in disaster_type
--   I4  admin_role enum + phone/department on admin_profiles
--   I5  logo/website/rating/suspended_reason on ngo_profiles
--   I6  video/schedule/failedReason/createdByType on social_posts
--   I7  estimatedDuration/createdByType/approvedAt on tasks
--   M1  CHECK on tasks.task_label non-empty
--   M2  CHECK on notifications.title non-empty
--   M3  read_at on notifications
--   N2  precautions/estimated_damage/analyzed_at on disaster_events
-- ============================================================================


-- ============================================================================
-- STEP 0: CLEAN SLATE
-- ============================================================================

DROP VIEW IF EXISTS social_posts_frontend_view CASCADE;
DROP VIEW IF EXISTS disaster_event_metrics CASCADE;
DROP VIEW IF EXISTS active_social_posts CASCADE;
DROP VIEW IF EXISTS active_tasks CASCADE;
DROP VIEW IF EXISTS active_disaster_events CASCADE;
DROP VIEW IF EXISTS active_alerts CASCADE;
DROP VIEW IF EXISTS active_ngo_profiles CASCADE;
DROP VIEW IF EXISTS active_admin_profiles CASCADE;
DROP VIEW IF EXISTS active_users CASCADE;

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS social_post_platforms CASCADE;
DROP TABLE IF EXISTS social_posts CASCADE;
DROP TABLE IF EXISTS task_status_history CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS disaster_sources CASCADE;
DROP TABLE IF EXISTS disaster_events CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS ngo_operational_areas CASCADE;
DROP TABLE IF EXISTS ngo_specializations CASCADE;
DROP TABLE IF EXISTS ngo_resources CASCADE;
DROP TABLE IF EXISTS ngo_profiles CASCADE;
DROP TABLE IF EXISTS notification_preferences CASCADE;
DROP TABLE IF EXISTS admin_profiles CASCADE;
DROP TABLE IF EXISTS auth_verification_tokens CASCADE;
DROP TABLE IF EXISTS auth_refresh_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Future-scope cleanup
DROP TABLE IF EXISTS news_sources CASCADE;
DROP TABLE IF EXISTS news_reports CASCADE;
DROP TABLE IF EXISTS volunteer_capabilities CASCADE;
DROP TABLE IF EXISTS volunteer_profiles CASCADE;
DROP TABLE IF EXISTS social_alerts CASCADE;

DROP TYPE IF EXISTS auth_token_purpose CASCADE;
DROP TYPE IF EXISTS social_post_status CASCADE;
DROP TYPE IF EXISTS social_platform CASCADE;
DROP TYPE IF EXISTS notification_type CASCADE;
DROP TYPE IF EXISTS verification_status CASCADE;
DROP TYPE IF EXISTS task_priority CASCADE;
DROP TYPE IF EXISTS task_status CASCADE;
DROP TYPE IF EXISTS task_type CASCADE;
DROP TYPE IF EXISTS alert_source CASCADE;
DROP TYPE IF EXISTS risk_level CASCADE;
DROP TYPE IF EXISTS disaster_event_status CASCADE;
DROP TYPE IF EXISTS alert_status CASCADE;
DROP TYPE IF EXISTS disaster_type CASCADE;
DROP TYPE IF EXISTS admin_role CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

DROP FUNCTION IF EXISTS touch_social_post_updated_at() CASCADE;
DROP FUNCTION IF EXISTS create_default_notification_preferences() CASCADE;
DROP FUNCTION IF EXISTS validate_ngo_profile_user_role() CASCADE;
DROP FUNCTION IF EXISTS validate_admin_profile_user_role() CASCADE;
DROP FUNCTION IF EXISTS trigger_set_updated_at() CASCADE;


-- ============================================================================
-- STEP 1: EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS citext;


-- ============================================================================
-- STEP 2: SESSION TIMEZONE
-- ============================================================================

SET TIME ZONE 'UTC';


-- ============================================================================
-- STEP 3: SHARED FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_admin_profile_user_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM users
        WHERE user_id = NEW.admin_id
          AND role = 'admin'
          AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'admin_profiles.admin_id must reference an active user with role = admin';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_ngo_profile_user_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM users
        WHERE user_id = NEW.ngo_id
          AND role = 'ngo_user'
          AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'ngo_profiles.ngo_id must reference an active user with role = ngo_user';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- STEP 4: ENUM TYPES (15 total)
-- ============================================================================

CREATE TYPE user_role AS ENUM ('admin', 'ngo_user');

CREATE TYPE admin_role AS ENUM ('super_admin', 'admin', 'moderator');

CREATE TYPE disaster_type AS ENUM (
    'flood', 'earthquake', 'cyclone', 'drought', 'heatwave', 'landslide'
);

CREATE TYPE alert_status AS ENUM (
    'new', 'verified', 'analyzing', 'active', 'monitoring', 'resolved', 'false_alarm'
);

CREATE TYPE disaster_event_status AS ENUM ('active', 'monitoring', 'resolved');

CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TYPE alert_source AS ENUM (
    'sensor', 'social_media', 'news', 'government', 'citizen', 'ai', 'manual'
);

CREATE TYPE task_type AS ENUM (
    'ambulance', 'boat', 'medical', 'food', 'evacuation', 'shelter'
);

CREATE TYPE task_status AS ENUM (
    'draft', 'pending_approval', 'unallocated',
    'pending_acceptance', 'assigned', 'in_progress', 'completed'
);

CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TYPE verification_status AS ENUM ('pending', 'verified', 'suspended', 'rejected');

CREATE TYPE notification_type AS ENUM (
    'task_assigned', 'task_updated', 'urgent_request', 'disaster_alert', 'system'
);

CREATE TYPE social_platform AS ENUM ('twitter', 'facebook', 'linkedin', 'tiktok');

CREATE TYPE social_post_status AS ENUM (
    'draft', 'queued', 'publishing', 'published', 'failed'
);

CREATE TYPE auth_token_purpose AS ENUM ('email_verification', 'password_reset');


-- ============================================================================
-- TABLE 1: USERS — Central auth
-- ============================================================================

CREATE TABLE users (
    user_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                citext NOT NULL,            -- no inline UNIQUE (see partial index below)
    password_hash        TEXT NOT NULL,
    role                 user_role NOT NULL,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified       BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at    TIMESTAMPTZ,
    last_login_at        TIMESTAMPTZ,
    password_changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT users_password_hash_length_chk CHECK (char_length(password_hash) >= 60)
);

-- FIX C1: partial unique so soft-deleted emails can be re-registered
CREATE UNIQUE INDEX idx_users_email_unique_active
    ON users(email) WHERE deleted_at IS NULL;

CREATE INDEX idx_users_role_active
    ON users(role) WHERE deleted_at IS NULL;

CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 2: ADMIN_PROFILES — FIX I4: added admin_role, phone, department
-- ============================================================================

CREATE TABLE admin_profiles (
    admin_id     UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE RESTRICT,
    full_name    VARCHAR(255) NOT NULL,
    avatar_url   TEXT,
    admin_role   admin_role NOT NULL DEFAULT 'admin',
    phone        VARCHAR(20),
    department   VARCHAR(100),
    is_online    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT admin_profiles_full_name_chk CHECK (char_length(trim(full_name)) > 0)
);

CREATE INDEX idx_admin_profiles_active
    ON admin_profiles(admin_id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_validate_admin_profile_user_role
    BEFORE INSERT OR UPDATE ON admin_profiles FOR EACH ROW
    EXECUTE FUNCTION validate_admin_profile_user_role();

CREATE TRIGGER set_admin_profiles_updated_at
    BEFORE UPDATE ON admin_profiles FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 3: NOTIFICATION_PREFERENCES
-- ============================================================================

CREATE TABLE notification_preferences (
    user_id            UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    email_alerts       BOOLEAN NOT NULL DEFAULT TRUE,
    sms_alerts         BOOLEAN NOT NULL DEFAULT FALSE,
    task_assignments   BOOLEAN NOT NULL DEFAULT TRUE,
    disaster_alerts    BOOLEAN NOT NULL DEFAULT TRUE,
    system_updates     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER set_notification_preferences_updated_at
    BEFORE UPDATE ON notification_preferences FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE OR REPLACE FUNCTION create_default_notification_preferences()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notification_preferences (user_id)
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_create_default_notification_preferences
    AFTER INSERT ON users FOR EACH ROW
    EXECUTE FUNCTION create_default_notification_preferences();


-- ============================================================================
-- TABLE 4: AUTH_REFRESH_TOKENS
-- ============================================================================

CREATE TABLE auth_refresh_tokens (
    refresh_token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_id       UUID NOT NULL DEFAULT gen_random_uuid(),
    token_hash       TEXT NOT NULL UNIQUE,
    parent_token_id  UUID REFERENCES auth_refresh_tokens(refresh_token_id) ON DELETE SET NULL,
    issued_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL,
    last_used_at     TIMESTAMPTZ,
    revoked_at       TIMESTAMPTZ,
    revoke_reason    TEXT,
    ip_address       INET,
    user_agent       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT auth_refresh_tokens_expiry_chk CHECK (expires_at > issued_at)
);

CREATE INDEX idx_refresh_tokens_user_active
    ON auth_refresh_tokens(user_id) WHERE revoked_at IS NULL;

CREATE INDEX idx_refresh_tokens_session
    ON auth_refresh_tokens(session_id);

CREATE INDEX idx_refresh_tokens_expires
    ON auth_refresh_tokens(expires_at);

CREATE TRIGGER set_refresh_tokens_updated_at
    BEFORE UPDATE ON auth_refresh_tokens FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 5: AUTH_VERIFICATION_TOKENS
-- ============================================================================

CREATE TABLE auth_verification_tokens (
    verification_token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    email                 citext NOT NULL,
    purpose               auth_token_purpose NOT NULL,
    token_hash            TEXT NOT NULL,
    expires_at            TIMESTAMPTZ NOT NULL,
    used_at               TIMESTAMPTZ,
    revoked_at            TIMESTAMPTZ,
    attempts_count        SMALLINT NOT NULL DEFAULT 0,
    max_attempts          SMALLINT NOT NULL DEFAULT 5,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT verification_tokens_attempts_chk CHECK (attempts_count >= 0),
    CONSTRAINT verification_tokens_max_attempts_chk CHECK (max_attempts > 0),
    CONSTRAINT verification_tokens_expiry_chk CHECK (expires_at > created_at)
);

CREATE INDEX idx_verification_tokens_user_purpose
    ON auth_verification_tokens(user_id, purpose);

CREATE INDEX idx_verification_tokens_email_purpose
    ON auth_verification_tokens(email, purpose);

CREATE UNIQUE INDEX idx_verification_tokens_one_open
    ON auth_verification_tokens(user_id, purpose)
    WHERE used_at IS NULL AND revoked_at IS NULL;

CREATE INDEX idx_verification_tokens_expires
    ON auth_verification_tokens(expires_at);

CREATE TRIGGER set_verification_tokens_updated_at
    BEFORE UPDATE ON auth_verification_tokens FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 6: NGO_PROFILES — FIX I5: added logo, website, rating, suspended_reason
-- ============================================================================

CREATE TABLE ngo_profiles (
    ngo_id              UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE RESTRICT,
    org_name            VARCHAR(255) NOT NULL,
    org_email           citext NOT NULL,
    registration_number VARCHAR(100) NOT NULL UNIQUE,
    head_of_operations  VARCHAR(255),
    phone               VARCHAR(20),
    phone_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    logo_url            TEXT,
    website             TEXT,
    base_city           VARCHAR(100),
    base_district       VARCHAR(100),
    base_province       VARCHAR(100),
    base_location       GEOGRAPHY(POINT, 4326),
    service_radius_km   INT NOT NULL DEFAULT 10,
    verification_status verification_status NOT NULL DEFAULT 'pending',
    verified_by         UUID REFERENCES users(user_id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    suspended_reason    TEXT,
    rating              DECIMAL(2,1) NOT NULL DEFAULT 0.0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT ngo_profiles_org_name_chk CHECK (char_length(trim(org_name)) > 0),
    CONSTRAINT ngo_profiles_org_email_chk CHECK (char_length(trim(org_email::text)) > 0),
    CONSTRAINT ngo_profiles_service_radius_chk CHECK (service_radius_km > 0),
    CONSTRAINT ngo_profiles_rating_chk CHECK (rating >= 0.0 AND rating <= 5.0)
);

CREATE UNIQUE INDEX idx_ngo_org_email_active
    ON ngo_profiles(org_email) WHERE deleted_at IS NULL;

CREATE INDEX idx_ngo_location
    ON ngo_profiles USING GIST(base_location);

CREATE INDEX idx_ngo_active
    ON ngo_profiles(ngo_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_ngo_verification_status
    ON ngo_profiles(verification_status) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_validate_ngo_profile_user_role
    BEFORE INSERT OR UPDATE ON ngo_profiles FOR EACH ROW
    EXECUTE FUNCTION validate_ngo_profile_user_role();

CREATE TRIGGER set_ngo_profiles_updated_at
    BEFORE UPDATE ON ngo_profiles FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 7: NGO_RESOURCES — 1:1 with ngo_profiles
-- ============================================================================

CREATE TABLE ngo_resources (
    ngo_id                UUID PRIMARY KEY REFERENCES ngo_profiles(ngo_id) ON DELETE CASCADE,
    ambulances            INT NOT NULL DEFAULT 0,
    rescue_boats          INT NOT NULL DEFAULT 0,
    trucks                INT NOT NULL DEFAULT 0,
    four_wheel_vehicles   INT NOT NULL DEFAULT 0,
    cranes                INT NOT NULL DEFAULT 0,
    doctors               INT NOT NULL DEFAULT 0,
    paramedics            INT NOT NULL DEFAULT 0,
    rescue_divers         INT NOT NULL DEFAULT 0,
    volunteers_available  INT NOT NULL DEFAULT 0,
    food_packets_capacity INT NOT NULL DEFAULT 0,
    shelter_capacity      INT NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ngo_res_ambulances_chk CHECK (ambulances >= 0),
    CONSTRAINT ngo_res_rescue_boats_chk CHECK (rescue_boats >= 0),
    CONSTRAINT ngo_res_trucks_chk CHECK (trucks >= 0),
    CONSTRAINT ngo_res_four_wheel_chk CHECK (four_wheel_vehicles >= 0),
    CONSTRAINT ngo_res_cranes_chk CHECK (cranes >= 0),
    CONSTRAINT ngo_res_doctors_chk CHECK (doctors >= 0),
    CONSTRAINT ngo_res_paramedics_chk CHECK (paramedics >= 0),
    CONSTRAINT ngo_res_divers_chk CHECK (rescue_divers >= 0),
    CONSTRAINT ngo_res_volunteers_chk CHECK (volunteers_available >= 0),
    CONSTRAINT ngo_res_food_chk CHECK (food_packets_capacity >= 0),
    CONSTRAINT ngo_res_shelter_chk CHECK (shelter_capacity >= 0)
);

CREATE TRIGGER set_ngo_resources_updated_at
    BEFORE UPDATE ON ngo_resources FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 8: NGO_SPECIALIZATIONS — FIX C2: unique per NGO
-- ============================================================================

CREATE TABLE ngo_specializations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id         UUID NOT NULL REFERENCES ngo_profiles(ngo_id) ON DELETE CASCADE,
    specialization VARCHAR(50) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ngo_spec_name_chk CHECK (char_length(trim(specialization)) > 0),
    CONSTRAINT ngo_spec_unique_per_ngo UNIQUE (ngo_id, specialization)
);

CREATE INDEX idx_ngo_spec_specialization
    ON ngo_specializations(specialization);


-- ============================================================================
-- TABLE 9: NGO_OPERATIONAL_AREAS — FIX C3: unique per NGO
-- ============================================================================

CREATE TABLE ngo_operational_areas (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id     UUID NOT NULL REFERENCES ngo_profiles(ngo_id) ON DELETE CASCADE,
    province   VARCHAR(100) NOT NULL,
    district   VARCHAR(100) NOT NULL,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ngo_area_province_chk CHECK (char_length(trim(province)) > 0),
    CONSTRAINT ngo_area_district_chk CHECK (char_length(trim(district)) > 0),
    CONSTRAINT ngo_area_unique_per_ngo UNIQUE (ngo_id, province, district)
);

CREATE INDEX idx_ngo_areas_ngo
    ON ngo_operational_areas(ngo_id);


-- ============================================================================
-- TABLE 10: ALERTS — FIX I1: source_name, FIX I2: false_alarm in enum
-- ============================================================================

CREATE TABLE alerts (
    alert_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_ref_id    VARCHAR(100),
    alert_type         disaster_type NOT NULL,
    title              VARCHAR(255) NOT NULL,
    description        TEXT,
    source_type        alert_source NOT NULL,
    source_name        VARCHAR(255),               -- e.g. "USGS", "Open-Meteo", "Google Flood Hub"
    status             alert_status NOT NULL DEFAULT 'new',
    severity_score     DECIMAL(3,1),
    confidence_score   DECIMAL(5,2),
    location           GEOGRAPHY(POINT, 4326) NOT NULL,
    location_name      VARCHAR(255),
    district           VARCHAR(100),
    province           VARCHAR(100),
    created_by         UUID REFERENCES users(user_id) ON DELETE SET NULL,
    verified_by        UUID REFERENCES users(user_id) ON DELETE SET NULL,
    detected_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT alerts_title_chk CHECK (char_length(trim(title)) > 0),
    CONSTRAINT alerts_severity_chk CHECK (severity_score IS NULL OR (severity_score >= 0 AND severity_score <= 10)),
    CONSTRAINT alerts_confidence_chk CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)),
    CONSTRAINT alerts_verified_after_detected_chk CHECK (verified_at IS NULL OR verified_at >= detected_at)
);

CREATE INDEX idx_alerts_location ON alerts USING GIST(location);
CREATE INDEX idx_alerts_status ON alerts(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_alerts_source ON alerts(source_type) WHERE deleted_at IS NULL;

CREATE TRIGGER set_alerts_updated_at
    BEFORE UPDATE ON alerts FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 11: DISASTER_EVENTS — N2: added precautions, damage, analyzed_at
-- ============================================================================

CREATE TABLE disaster_events (
    event_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_alert_id      UUID UNIQUE REFERENCES alerts(alert_id) ON DELETE SET NULL,
    external_ref_id      VARCHAR(100),
    event_type           disaster_type NOT NULL,
    title                VARCHAR(255) NOT NULL,
    description          TEXT,
    location_name        VARCHAR(255),
    district             VARCHAR(100),
    province             VARCHAR(100),
    location             GEOGRAPHY(POINT, 4326) NOT NULL,
    affected_area        GEOGRAPHY(POLYGON, 4326),
    affected_population  INT,
    severity_score       DECIMAL(3,1),
    risk_level           risk_level,
    source_type          alert_source,
    event_status         disaster_event_status NOT NULL DEFAULT 'active',
    precautions          TEXT[],
    estimated_damage_pkr BIGINT,
    created_by           UUID REFERENCES users(user_id) ON DELETE SET NULL,
    verified_by          UUID REFERENCES users(user_id) ON DELETE SET NULL,
    detected_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at          TIMESTAMPTZ,
    analyzed_at          TIMESTAMPTZ,
    resolved_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT de_title_chk CHECK (char_length(trim(title)) > 0),
    CONSTRAINT de_population_chk CHECK (affected_population IS NULL OR affected_population >= 0),
    CONSTRAINT de_severity_chk CHECK (severity_score IS NULL OR (severity_score >= 0 AND severity_score <= 10)),
    CONSTRAINT de_damage_chk CHECK (estimated_damage_pkr IS NULL OR estimated_damage_pkr >= 0),
    CONSTRAINT de_verified_after_detected_chk CHECK (verified_at IS NULL OR verified_at >= detected_at),
    CONSTRAINT de_analyzed_after_detected_chk CHECK (analyzed_at IS NULL OR analyzed_at >= detected_at),
    CONSTRAINT de_resolved_after_detected_chk CHECK (resolved_at IS NULL OR resolved_at >= detected_at)
);

CREATE INDEX idx_de_location ON disaster_events USING GIST(location);
CREATE INDEX idx_de_status ON disaster_events(event_status) WHERE deleted_at IS NULL;
CREATE INDEX idx_de_source_alert ON disaster_events(source_alert_id) WHERE deleted_at IS NULL;

CREATE TRIGGER set_disaster_events_updated_at
    BEFORE UPDATE ON disaster_events FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 12: DISASTER_SOURCES — append-only provenance
-- ============================================================================

CREATE TABLE disaster_sources (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id         UUID NOT NULL REFERENCES disaster_events(event_id) ON DELETE CASCADE,
    source_type      alert_source,
    source_name      VARCHAR(255),
    source_url       TEXT,
    raw_data         JSONB,
    confidence_score DECIMAL(5,2),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ds_confidence_chk CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100))
);

CREATE INDEX idx_ds_event ON disaster_sources(event_id);


-- ============================================================================
-- TABLE 13: TASKS — FIX I7 + M1: all missing columns + label check
-- ============================================================================

CREATE TABLE tasks (
    task_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id              UUID REFERENCES disaster_events(event_id) ON DELETE RESTRICT,
    task_label            VARCHAR(255) NOT NULL,
    description           TEXT,
    task_type             task_type NOT NULL,
    required_quantity     INT,
    priority              task_priority NOT NULL DEFAULT 'medium',
    target_location       GEOGRAPHY(POINT, 4326),
    target_location_name  VARCHAR(255),
    status                task_status NOT NULL DEFAULT 'draft',
    created_by_type       VARCHAR(10) NOT NULL DEFAULT 'admin',
    admin_approved_by     UUID REFERENCES users(user_id) ON DELETE SET NULL,
    approved_at           TIMESTAMPTZ,
    assigned_ngo_id       UUID REFERENCES ngo_profiles(ngo_id) ON DELETE SET NULL,
    progress              INT NOT NULL DEFAULT 0,
    estimated_duration_hours INT,
    proof_image_url       TEXT,
    assigned_at           TIMESTAMPTZ,
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ,
    completion_notes      TEXT,
    deadline              TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT tasks_label_chk CHECK (char_length(trim(task_label)) > 0),
    CONSTRAINT tasks_progress_chk CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT tasks_quantity_chk CHECK (required_quantity IS NULL OR required_quantity >= 0),
    CONSTRAINT tasks_duration_chk CHECK (estimated_duration_hours IS NULL OR estimated_duration_hours > 0),
    CONSTRAINT tasks_created_by_type_chk CHECK (created_by_type IN ('ai', 'admin'))
);

CREATE INDEX idx_task_location ON tasks USING GIST(target_location);
CREATE INDEX idx_task_status ON tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_task_ngo ON tasks(assigned_ngo_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_task_event ON tasks(event_id) WHERE deleted_at IS NULL;

CREATE TRIGGER set_tasks_updated_at
    BEFORE UPDATE ON tasks FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 14: TASK_STATUS_HISTORY — immutable audit
-- ============================================================================

CREATE TABLE task_status_history (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    old_status    task_status,
    new_status    task_status NOT NULL,
    changed_by    UUID REFERENCES users(user_id) ON DELETE SET NULL,
    change_reason TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_task_history_task ON task_status_history(task_id);


-- ============================================================================
-- TABLE 15: SOCIAL_POSTS — FIX I6: video, schedule, failed, createdByType
-- ============================================================================

CREATE TABLE social_posts (
    social_post_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id           UUID REFERENCES disaster_events(event_id) ON DELETE SET NULL,
    content_text       TEXT,
    content_image_url  TEXT,
    video_url          TEXT,
    status             social_post_status NOT NULL DEFAULT 'draft',
    created_by         UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_by_type    VARCHAR(10) NOT NULL DEFAULT 'admin',
    scheduled_at       TIMESTAMPTZ,
    failed_reason      TEXT,
    published_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at         TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT sp_content_chk CHECK (
        (content_text IS NOT NULL AND char_length(trim(content_text)) > 0)
        OR content_image_url IS NOT NULL
        OR video_url IS NOT NULL
    ),
    CONSTRAINT sp_created_by_type_chk CHECK (created_by_type IN ('ai', 'admin'))
);

CREATE INDEX idx_sp_event ON social_posts(event_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sp_status ON social_posts(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_sp_created_by ON social_posts(created_by) WHERE deleted_at IS NULL;

CREATE TRIGGER set_social_posts_updated_at
    BEFORE UPDATE ON social_posts FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================================
-- TABLE 16: SOCIAL_POST_PLATFORMS — per-platform state + engagement
-- ============================================================================

CREATE TABLE social_post_platforms (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_post_id  UUID NOT NULL REFERENCES social_posts(social_post_id) ON DELETE CASCADE,
    platform        social_platform NOT NULL,
    status          social_post_status NOT NULL DEFAULT 'queued',
    post_url        TEXT,
    failed_reason   TEXT,
    published_at    TIMESTAMPTZ,
    views           INT NOT NULL DEFAULT 0,
    likes           INT NOT NULL DEFAULT 0,
    shares          INT NOT NULL DEFAULT 0,
    comments        INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT spp_unique_post_platform UNIQUE (social_post_id, platform),
    CONSTRAINT spp_views_chk CHECK (views >= 0),
    CONSTRAINT spp_likes_chk CHECK (likes >= 0),
    CONSTRAINT spp_shares_chk CHECK (shares >= 0),
    CONSTRAINT spp_comments_chk CHECK (comments >= 0)
);

CREATE INDEX idx_spp_post ON social_post_platforms(social_post_id);
CREATE INDEX idx_spp_platform ON social_post_platforms(platform);

CREATE TRIGGER set_spp_updated_at
    BEFORE UPDATE ON social_post_platforms FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- Auto-touch parent updated_at when child changes
CREATE OR REPLACE FUNCTION touch_social_post_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE social_posts SET updated_at = now()
    WHERE social_post_id = COALESCE(NEW.social_post_id, OLD.social_post_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_touch_sp_after_platform_insert
    AFTER INSERT ON social_post_platforms FOR EACH ROW
    EXECUTE FUNCTION touch_social_post_updated_at();

CREATE TRIGGER trg_touch_sp_after_platform_update
    AFTER UPDATE ON social_post_platforms FOR EACH ROW
    EXECUTE FUNCTION touch_social_post_updated_at();

CREATE TRIGGER trg_touch_sp_after_platform_delete
    AFTER DELETE ON social_post_platforms FOR EACH ROW
    EXECUTE FUNCTION touch_social_post_updated_at();


-- ============================================================================
-- TABLE 17: NOTIFICATIONS — FIX M2 + M3: title check, read_at
-- ============================================================================

CREATE TABLE notifications (
    notification_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID REFERENCES users(user_id) ON DELETE CASCADE,
    title             VARCHAR(255) NOT NULL,
    message           TEXT,
    notification_type notification_type NOT NULL,
    related_task_id   UUID REFERENCES tasks(task_id) ON DELETE SET NULL,
    related_event_id  UUID REFERENCES disaster_events(event_id) ON DELETE SET NULL,
    changes           JSONB,
    is_read           BOOLEAN NOT NULL DEFAULT FALSE,
    read_at           TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT notif_title_chk CHECK (char_length(trim(title)) > 0),
    CONSTRAINT notif_changes_is_array_chk CHECK (changes IS NULL OR jsonb_typeof(changes) = 'array')
);

CREATE INDEX idx_notif_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notif_task ON notifications(related_task_id);
CREATE INDEX idx_notif_event ON notifications(related_event_id);


-- ============================================================================
-- TABLE 18: AUDIT_LOGS — immutable
-- ============================================================================

CREATE TABLE audit_logs (
    log_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action       VARCHAR(100) NOT NULL,
    entity_type  VARCHAR(50),
    entity_id    UUID,
    old_values   JSONB,
    new_values   JSONB,
    ip_address   INET,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);


-- ============================================================================
-- VIEWS
-- ============================================================================

CREATE VIEW active_users AS
    SELECT * FROM users WHERE deleted_at IS NULL;

CREATE VIEW active_admin_profiles AS
    SELECT * FROM admin_profiles WHERE deleted_at IS NULL;

CREATE VIEW active_ngo_profiles AS
    SELECT * FROM ngo_profiles WHERE deleted_at IS NULL;

CREATE VIEW active_alerts AS
    SELECT * FROM alerts WHERE deleted_at IS NULL;

CREATE VIEW active_disaster_events AS
    SELECT * FROM disaster_events WHERE deleted_at IS NULL;

CREATE VIEW active_tasks AS
    SELECT * FROM tasks WHERE deleted_at IS NULL;

CREATE VIEW active_social_posts AS
    SELECT * FROM social_posts WHERE deleted_at IS NULL;


-- ============================================================================
-- VIEW: DISASTER_EVENT_METRICS — computed task counts per disaster
-- ============================================================================

CREATE VIEW disaster_event_metrics AS
SELECT
    de.event_id,
    COUNT(t.task_id) FILTER (WHERE t.deleted_at IS NULL)
        AS total_tasks,
    COUNT(t.task_id) FILTER (WHERE t.deleted_at IS NULL AND t.status = 'completed')
        AS completed_tasks,
    COUNT(t.task_id) FILTER (WHERE t.deleted_at IS NULL AND t.status = 'in_progress')
        AS in_progress_tasks,
    COUNT(t.task_id) FILTER (WHERE t.deleted_at IS NULL AND t.status = 'unallocated')
        AS unallocated_tasks,
    COUNT(DISTINCT t.assigned_ngo_id) FILTER (WHERE t.deleted_at IS NULL AND t.assigned_ngo_id IS NOT NULL)
        AS assigned_ngos
FROM disaster_events de
LEFT JOIN tasks t ON t.event_id = de.event_id
WHERE de.deleted_at IS NULL
GROUP BY de.event_id;


-- ============================================================================
-- VIEW: SOCIAL_POSTS_FRONTEND_VIEW — aggregated platforms + engagement
-- ============================================================================

CREATE VIEW social_posts_frontend_view AS
SELECT
    sp.social_post_id,
    sp.event_id,
    sp.content_text,
    sp.content_image_url,
    sp.video_url,
    sp.status,
    sp.created_by,
    sp.created_by_type,
    sp.scheduled_at,
    sp.failed_reason,
    sp.published_at,
    sp.created_at,
    sp.updated_at,
    COALESCE(
        ARRAY_AGG(spp.platform ORDER BY spp.platform)
            FILTER (WHERE spp.platform IS NOT NULL),
        ARRAY[]::social_platform[]
    ) AS platforms,
    COALESCE(SUM(spp.views), 0)    AS engagement_views,
    COALESCE(SUM(spp.likes), 0)    AS engagement_likes,
    COALESCE(SUM(spp.shares), 0)   AS engagement_shares,
    COALESCE(SUM(spp.comments), 0) AS engagement_comments
FROM social_posts sp
LEFT JOIN social_post_platforms spp ON spp.social_post_id = sp.social_post_id
WHERE sp.deleted_at IS NULL
GROUP BY
    sp.social_post_id, sp.event_id, sp.content_text, sp.content_image_url,
    sp.video_url, sp.status, sp.created_by, sp.created_by_type,
    sp.scheduled_at, sp.failed_reason, sp.published_at,
    sp.created_at, sp.updated_at;


-- ============================================================================
-- DONE — 18 tables, 8 views, 15 enums, all issues resolved
-- ============================================================================
