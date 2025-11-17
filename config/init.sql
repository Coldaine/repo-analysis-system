-- PostgreSQL Database Initialization Script
-- Run this once to initialize the database schema

-- This script creates the database schema for the Repository Analysis System
-- It should be run after PostgreSQL is started and before the application

-- Usage:
--   docker exec -i postgres psql -U postgres -d repo_analysis -f /docker-entrypoint-initdb.d/init.sql

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS repo_analysis;

-- Connect to the database
\c repo_analysis

-- Run the schema creation
\i src/storage/schema.sql

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_repositories_active ON repositories(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_repositories_monitored ON repositories(is_monitored) WHERE is_monitored = true;
CREATE INDEX IF NOT EXISTS idx_repositories_owner_name ON repositories(owner, name);
CREATE INDEX IF NOT EXISTS idx_baselines_repo_id ON baselines(repo_id);
CREATE INDEX IF NOT EXISTS idx_baselines_active ON baselines(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_baselines_hash ON baselines(hash);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_repo_id ON analysis_runs(repo_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at ON analysis_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_pull_requests_run_id ON pull_requests(run_id);
CREATE INDEX IF NOT EXISTS idx_pull_requests_state ON pull_requests(state);
CREATE INDEX IF NOT EXISTS idx_pain_points_run_id ON pain_points(run_id);
CREATE INDEX IF NOT EXISTS idx_pain_points_type ON pain_points(type);
CREATE INDEX IF NOT EXISTS idx_pain_points_severity ON pain_points(severity);
CREATE INDEX IF NOT EXISTS idx_recommendations_pain_point_id ON recommendations(pain_point_id);
CREATE INDEX IF NOT EXISTS idx_visualizations_run_id ON visualizations(run_id);
CREATE INDEX IF NOT EXISTS idx_visualizations_type ON visualizations(type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON system_metrics(metric_name, recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Insert initial data if needed
-- Add any default users or repositories here

-- Grant permissions to application user
-- Note: In production, create a dedicated application user with limited permissions
-- GRANT CONNECT ON DATABASE repo_analysis TO repo_analysis_app;
-- GRANT USAGE ON SCHEMA public TO repo_analysis_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO repo_analysis_app;

COMMIT;

-- Output success message
\echo 'Database schema initialized successfully'