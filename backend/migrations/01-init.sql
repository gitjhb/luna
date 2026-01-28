-- AI Companion Platform - Database Initialization Script
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for performance (these will be created by SQLAlchemy, but we can pre-create them)
-- Note: Tables will be created by the application on first run

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_companion TO postgres;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
