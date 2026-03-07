-- migrations/add_effect_columns.sql
-- Add missing columns to active_effects table for stage boost, NSFW override, and XP multiplier

ALTER TABLE active_effects ADD COLUMN stage_boost INTEGER DEFAULT 0;
ALTER TABLE active_effects ADD COLUMN allows_nsfw INTEGER DEFAULT 0;
ALTER TABLE active_effects ADD COLUMN xp_multiplier REAL DEFAULT 1.0;
