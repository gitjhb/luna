-- Migration: Add is_extended column to date_sessions table
-- Date: 2025-01-xx
-- Description: Adds is_extended boolean column to persist the date extension state

-- Check if column exists before adding (SQLite compatible)
-- For SQLite, we need to use a different approach since ALTER TABLE ADD COLUMN 
-- will fail if column exists

-- First, try to add the column (this will fail silently if column already exists in SQLite)
ALTER TABLE date_sessions ADD COLUMN is_extended BOOLEAN DEFAULT FALSE;

-- For PostgreSQL, you might need:
-- ALTER TABLE date_sessions ADD COLUMN IF NOT EXISTS is_extended BOOLEAN DEFAULT FALSE;
