-- PostgreSQL Database Schema for Portfolio Rebalancer
-- This file initializes the database schema for event tracking

-- Create database if it doesn't exist (handled by docker-compose)
-- CREATE DATABASE IF NOT EXISTS portfolio_rebalancer;

-- Event tracking table
CREATE TABLE IF NOT EXISTS rebalance_events (
    event_id UUID PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    payload JSONB NOT NULL,
    error_message TEXT,
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    first_failed_date DATE,
    times_queued INTEGER DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_account_id ON rebalance_events(account_id);
CREATE INDEX IF NOT EXISTS idx_events_status ON rebalance_events(status);
CREATE INDEX IF NOT EXISTS idx_events_received_at ON rebalance_events(received_at);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON rebalance_events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_event_id ON rebalance_events(event_id);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_events_account_status ON rebalance_events(account_id, status);
CREATE INDEX IF NOT EXISTS idx_events_status_created ON rebalance_events(status, created_at);

-- Insert test data (optional)
-- INSERT INTO rebalance_events (event_id, account_id, status, payload, received_at) 
-- VALUES 
--     ('550e8400-e29b-41d4-a716-446655440000', 'DUM959247', 'completed', '{"execution": "dry_run"}', NOW()),
--     ('550e8400-e29b-41d4-a716-446655440001', 'DU789012', 'pending', '{"execution": "rebalance"}', NOW());

-- Optional: Create a view for recent events
CREATE OR REPLACE VIEW recent_events AS
SELECT 
    event_id,
    account_id,
    status,
    payload,
    error_message,
    received_at,
    started_at,
    completed_at,
    (completed_at - started_at) AS processing_duration,
    retry_count,
    times_queued
FROM rebalance_events 
WHERE received_at >= NOW() - INTERVAL '7 days'
ORDER BY received_at DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rebalance_events TO postgres;
-- GRANT SELECT ON recent_events TO postgres;