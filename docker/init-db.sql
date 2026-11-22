-- Initialize openScience database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS openscience;

-- Create tables (example - adapt to your needs)
CREATE TABLE IF NOT EXISTS openscience.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data JSONB
);

CREATE TABLE IF NOT EXISTS openscience.results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES openscience.sessions(id),
    task_id VARCHAR(255),
    status VARCHAR(50),
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON openscience.sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_results_session_id ON openscience.results(session_id);
CREATE INDEX IF NOT EXISTS idx_results_task_id ON openscience.results(task_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA openscience TO openscience;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openscience TO openscience;
