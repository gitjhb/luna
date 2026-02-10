-- Migration: Add intro_shown column to chat_sessions
-- Date: 2026-02-09
-- Description: Track whether intro animation has been shown to user

ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS intro_shown BOOLEAN DEFAULT FALSE;
