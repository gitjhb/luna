-- Event Memories Table Migration
-- Stores generated story content for milestone events

-- Create table if not exists
CREATE TABLE IF NOT EXISTS event_memories (
    id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    character_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    story_content TEXT NOT NULL,
    context_summary TEXT,
    intimacy_level VARCHAR(32),
    emotion_state VARCHAR(32),
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_event_memory_user_id ON event_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_event_memory_character_id ON event_memories(character_id);
CREATE INDEX IF NOT EXISTS idx_event_memory_event_type ON event_memories(event_type);
CREATE INDEX IF NOT EXISTS idx_event_memory_user_character ON event_memories(user_id, character_id);

-- Create unique index to ensure one story per event per user-character pair
CREATE UNIQUE INDEX IF NOT EXISTS idx_event_memory_unique_event 
ON event_memories(user_id, character_id, event_type);

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Event memories table migration completed';
END $$;
