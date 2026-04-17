CREATE TABLE IF NOT EXISTS customer_wechat_bindings (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    openid VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    phone VARCHAR(32),
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    bound_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unbound_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_wechat_bindings_store_openid
    ON customer_wechat_bindings (store_id, openid);
CREATE INDEX IF NOT EXISTS idx_customer_wechat_bindings_store_partner
    ON customer_wechat_bindings (store_id, partner_id);
CREATE INDEX IF NOT EXISTS idx_customer_wechat_bindings_status
    ON customer_wechat_bindings (status);

CREATE TABLE IF NOT EXISTS customer_auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    binding_id BIGINT NOT NULL,
    session_token_hash VARCHAR(128) NOT NULL,
    refresh_token_hash VARCHAR(128),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    device_id VARCHAR(128),
    device_type VARCHAR(32),
    ip VARCHAR(64),
    user_agent VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_auth_sessions_session_hash
    ON customer_auth_sessions (session_token_hash);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_auth_sessions_refresh_hash
    ON customer_auth_sessions (refresh_token_hash)
    WHERE refresh_token_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customer_auth_sessions_store_partner
    ON customer_auth_sessions (store_id, partner_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS customer_subscription_prefs (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    vehicle_id BIGINT,
    notify_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    remind_before_days INTEGER NOT NULL DEFAULT 7,
    remind_before_km INTEGER NOT NULL DEFAULT 500,
    prefer_channel VARCHAR(32) NOT NULL DEFAULT 'wechat_subscribe',
    last_notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_subscription_prefs_store_partner_vehicle
    ON customer_subscription_prefs (store_id, partner_id, vehicle_id);
