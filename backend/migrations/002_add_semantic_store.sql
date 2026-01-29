-- Migration: Add Semantic Memory Store
-- Description: Creates tables for LangGraph semantic memory with vector search
-- Date: 2025-01-29
--
-- This enables:
-- - Long-term pattern storage for qualification
-- - Email success pattern matching
-- - Semantic search across stored memories

-- Enable pgvector extension (required for embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Semantic store table
CREATE TABLE IF NOT EXISTS semantic_store (
    id BIGSERIAL,
    namespace TEXT[] NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (namespace, key)
);

-- Index for namespace lookups
CREATE INDEX IF NOT EXISTS idx_semantic_namespace
    ON semantic_store(namespace);

-- Index for vector similarity search (cosine)
CREATE INDEX IF NOT EXISTS idx_semantic_embedding
    ON semantic_store USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Index for recent entries
CREATE INDEX IF NOT EXISTS idx_semantic_updated
    ON semantic_store(updated_at DESC);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_semantic_store_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_semantic_store_updated ON semantic_store;
CREATE TRIGGER trigger_semantic_store_updated
    BEFORE UPDATE ON semantic_store
    FOR EACH ROW
    EXECUTE FUNCTION update_semantic_store_timestamp();

-- Add comments for documentation
COMMENT ON TABLE semantic_store IS 'Long-term semantic memory for agent patterns and learnings';
COMMENT ON COLUMN semantic_store.namespace IS 'Hierarchical namespace (e.g., {qualification, patterns})';
COMMENT ON COLUMN semantic_store.key IS 'Unique key within namespace';
COMMENT ON COLUMN semantic_store.value IS 'Stored data (JSON)';
COMMENT ON COLUMN semantic_store.embedding IS 'Vector embedding for semantic search';
