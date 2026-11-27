-- ============================================================================
-- SMART IT HELPDESK MANAGEMENT SYSTEM
-- Script: 00_init_database_and_user.sql
-- Description: Creates the database and least-privilege application role.
-- Run this as superuser (postgres).
-- ============================================================================

-- Create database if it doesn't already exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'smart_helpdesk') THEN
        PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE smart_helpdesk WITH ENCODING = ''UTF8'' TEMPLATE = template1');
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- Fallback if dblink is not installed: direct CREATE DATABASE outside transaction block
        RAISE NOTICE 'Run: CREATE DATABASE smart_helpdesk WITH ENCODING = ''UTF8''; if not already created.';
END
$$;

-- Create application least-privilege role if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'helpdesk_app') THEN
        CREATE ROLE helpdesk_app WITH LOGIN PASSWORD 'helpdesk_secure_pass_phase2' NOSUPERUSER NOCREATEDB NOCREATEROLE;
        RAISE NOTICE 'Role helpdesk_app created.';
    ELSE
        ALTER ROLE helpdesk_app WITH PASSWORD 'helpdesk_secure_pass_phase2';
        RAISE NOTICE 'Role helpdesk_app updated.';
    END IF;
END
$$;

-- Connect instructions:
-- \c smart_helpdesk
-- GRANT CONNECT ON DATABASE smart_helpdesk TO helpdesk_app;
-- GRANT USAGE ON SCHEMA public TO helpdesk_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO helpdesk_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO helpdesk_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO helpdesk_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO helpdesk_app;
