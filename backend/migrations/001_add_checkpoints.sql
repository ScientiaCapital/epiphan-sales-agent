-- Migration: Add LangGraph Checkpoints Table
-- Description: Creates tables for LangGraph PostgresSaver checkpointing
-- Date: 2025-01-29
--
-- This enables:
-- - Human-in-the-loop workflows (pause/resume)
-- - State recovery on failure
-- - Time travel debugging

-- Checkpoints table (main state storage)
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Index for efficient parent lookup (time travel)
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent
    ON checkpoints(thread_id, checkpoint_ns, parent_checkpoint_id)
    WHERE parent_checkpoint_id IS NOT NULL;

-- Index for recent checkpoints lookup
CREATE INDEX IF NOT EXISTS idx_checkpoints_created
    ON checkpoints(thread_id, created_at DESC);

-- Checkpoint blobs table (for large binary data)
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

-- Checkpoint writes table (pending writes before commit)
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Add comments for documentation
COMMENT ON TABLE checkpoints IS 'LangGraph agent state checkpoints for persistence and human-in-the-loop workflows';
COMMENT ON TABLE checkpoint_blobs IS 'Binary data storage for large checkpoint values';
COMMENT ON TABLE checkpoint_writes IS 'Pending checkpoint writes before commit';
