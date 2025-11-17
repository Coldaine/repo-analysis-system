-- PostgreSQL Schema for Repository Analysis System
-- Designed for multi-user concurrent access

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User management for multi-user access
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Repository tracking
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    github_id INTEGER UNIQUE,
    description TEXT,
    language VARCHAR(100),
    last_sync TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    is_monitored BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, owner)
);

-- Baseline snapshots for repository goals and phases
CREATE TABLE baselines (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    goals JSONB NOT NULL,
    phases JSONB NOT NULL,
    metadata JSONB,
    hash VARCHAR(64) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis runs tracking
CREATE TABLE analysis_runs (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    baseline_id INTEGER REFERENCES baselines(id),
    run_type VARCHAR(50) DEFAULT 'full', -- full, incremental, webhook
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    metrics JSONB,
    error_message TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pull requests analyzed during runs
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    github_pr_id INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    state VARCHAR(20), -- open, closed, merged
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    merged_at TIMESTAMP WITH TIME ZONE,
    additions INTEGER,
    deletions INTEGER,
    changed_files INTEGER,
    metadata JSONB,
    UNIQUE(run_id, github_pr_id)
);

-- Pain points identified during analysis
CREATE TABLE pain_points (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    pr_id INTEGER REFERENCES pull_requests(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL, -- ci_inconsistency, merge_conflicts, code_quality, etc.
    severity INTEGER CHECK (severity >= 1 AND severity <= 5),
    description TEXT NOT NULL,
    raw_context JSONB,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Recommendations generated for pain points
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    pain_point_id INTEGER REFERENCES pain_points(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    source VARCHAR(100), -- glm_4_6, minimax, documentation, etc.
    source_url VARCHAR(500),
    rank INTEGER,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    is_accepted BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Generated visualizations
CREATE TABLE visualizations (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- timeline, gantt, flowchart, sequence, xychart
    title VARCHAR(255),
    description TEXT,
    mermaid_code TEXT,
    file_path VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System metrics and monitoring
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_unit VARCHAR(20),
    tags JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log for tracking changes
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes for concurrent access
CREATE INDEX idx_repositories_active ON repositories(is_active) WHERE is_active = true;
CREATE INDEX idx_repositories_monitored ON repositories(is_monitored) WHERE is_monitored = true;
CREATE INDEX idx_repositories_owner_name ON repositories(owner, name);

CREATE INDEX idx_baselines_repo_id ON baselines(repo_id);
CREATE INDEX idx_baselines_active ON baselines(is_active) WHERE is_active = true;
CREATE INDEX idx_baselines_hash ON baselines(hash);

CREATE INDEX idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX idx_analysis_runs_repo_id ON analysis_runs(repo_id);
CREATE INDEX idx_analysis_runs_created_at ON analysis_runs(created_at);
CREATE INDEX idx_analysis_runs_type_status ON analysis_runs(run_type, status);

CREATE INDEX idx_pull_requests_run_id ON pull_requests(run_id);
CREATE INDEX idx_pull_requests_state ON pull_requests(state);

CREATE INDEX idx_pain_points_run_id ON pain_points(run_id);
CREATE INDEX idx_pain_points_type ON pain_points(type);
CREATE INDEX idx_pain_points_severity ON pain_points(severity);
CREATE INDEX idx_pain_points_severity_type ON pain_points(severity, type);

CREATE INDEX idx_recommendations_pain_point_id ON recommendations(pain_point_id);
CREATE INDEX idx_recommendations_rank ON recommendations(rank);

CREATE INDEX idx_visualizations_run_id ON visualizations(run_id);
CREATE INDEX idx_visualizations_type ON visualizations(type);

CREATE INDEX idx_system_metrics_name_time ON system_metrics(metric_name, recorded_at);
CREATE INDEX idx_system_metrics_recorded_at ON system_metrics(recorded_at);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repositories_updated_at BEFORE UPDATE ON repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_baselines_updated_at BEFORE UPDATE ON baselines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_runs_updated_at BEFORE UPDATE ON analysis_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security for multi-tenant access (optional)
-- ALTER TABLE repositories ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE baselines ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (uncomment and customize as needed)
-- CREATE POLICY repository_access ON repositories
--     FOR ALL TO authenticated_user
--     USING (created_by = current_user_id());