-- Migration 053: add mode column to launch_projects
-- Allows the cockpit mode switcher to persist the building's lifecycle phase.

ALTER TABLE launch_projects
  ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'launch'
    CHECK (mode IN ('prospecting', 'active', 'launch', 'post_launch'));
