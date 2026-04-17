-- Rollback template for migration: 0004_customer_app_auth
-- WARNING: This is destructive. Backup DB before execution.

DROP TABLE IF EXISTS customer_subscription_prefs;
DROP TABLE IF EXISTS customer_auth_sessions;
DROP TABLE IF EXISTS customer_wechat_bindings;

DELETE FROM schema_migrations WHERE version = '0004_customer_app_auth';
