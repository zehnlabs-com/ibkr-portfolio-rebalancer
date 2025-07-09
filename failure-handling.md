# Failure Handling Implementation Plan

## Overview
This document outlines the systematic implementation of the new failure handling strategy for the event-processor system. The changes focus on indefinite event retention, improved deduplication, simplified retry logic, and a management service for monitoring and queue manipulation.

## Phase 1: Queue Event Tracking Enhancement
**Goal**: Add `times_queued` tracking and improve event deduplication

### 1.1 Event Structure Updates
- Add `times_queued` field to event data structure
- Initialize to 1 when event is first created in event-processor
- Increment on each requeue operation

### 1.2 Event Deduplication System (Event Broker)
- Modify event-broker deduplication from account-level to account+command-level
- Change deduplication key from `{account_id}` to `{account_id}:{exec_command}`
- Update Redis set from `queued_accounts` to `active_events`
- Allow multiple command types per account (e.g., `print-rebalance` + `cancel-orders`)
- Prevent duplicate commands per account (e.g., `rebalance` + `rebalance`)

### 1.3 Queue Service Modifications (Event Processor)
- Update `requeue_event()` to increment `times_queued`
- Update `remove_from_queued()` to use new deduplication keys
- Ensure compatibility with new event-broker deduplication system

## Phase 2: IBKR Connection Retry Simplification
**Goal**: Remove exponential backoff and jitter, use fixed delays

### 2.1 Configuration Updates
- Simplify retry config structure in `config.py` and `config.yaml`
- Remove `backoff_multiplier`, `jitter`, and `max_delay` fields
- Keep `max_retries` and rename `base_delay` to `delay` (fixed delay)
- Remove unused retry configuration parameters

### 2.2 Retry Logic Simplification
- Update `retry_with_config()` in `utils/retry.py` to use fixed delays
- Remove exponential backoff calculation
- Remove jitter logic
- Keep max_retries behavior with simple delay between attempts

### 2.3 IBKR Client Updates
- Update connection retry to use new simplified logic
- Ensure fast failure when max retries exceeded
- Remove unused retry configuration options

## Phase 3: Management Service Implementation
**Goal**: Create FastAPI service for queue management and health monitoring

### 3.1 Service Structure
- Create new `management-service/` directory
- Add FastAPI application with endpoints
- Add Docker configuration
- Add to docker-compose.yaml

### 3.2 Core Endpoints
- `GET /health` - Check for events with `times_queued > 1` (healthy if none exist)
- `GET /queue/status` - Queue length, stats, oldest event info
- `GET /queue/events` - List events with retry counts and details
- `DELETE /queue/events/{event_id}` - Remove specific event (API key required)
- `POST /queue/events` - Add event manually (API key required)

### 3.3 Security Implementation
- Add API key authentication for mutation operations (DELETE, POST)
- Secure DELETE and POST endpoints with header-based API key
- Add API key configuration via environment variable

### 3.4 Queue Management Logic
- Implement Redis queue inspection capabilities
- Add event manipulation capabilities (add/remove)
- Add proper error handling and logging
- Connect to same Redis instance as event-processor
- Work with new account+command-level deduplication system

## Phase 4: Event Processing Updates
**Goal**: Integrate new failure handling with event processor

### 4.1 Event Processing Flow
- Update event processing to work with new deduplication system
- Ensure proper `times_queued` tracking on requeue
- Update failure handling to use new simplified retry logic
- Maintain indefinite event retention (no dead letter queue)

### 4.2 Remove Health Command
- Remove `health_check.py` command file
- Update command factory to exclude health command
- Clean up related imports and references

### 4.3 Integration Updates
- Ensure event processor works with new queue service methods
- Update error handling to increment retry counters properly
- Maintain current account locking mechanism
- Update queue cleanup to use new deduplication keys

## Phase 5: Documentation and Configuration
**Goal**: Update documentation and ensure proper configuration

### 5.1 README Updates
- Document new error handling strategy
- Add management service usage instructions
- Add troubleshooting guide with common scenarios
- Document API endpoints and authentication

### 5.2 Configuration Management
- Update config.yaml with simplified retry settings
- Add management service configuration section
- Remove unused configuration parameters
- Add environment variable documentation for API keys

### 5.3 Docker and Deployment
- Update docker-compose.yaml to include management service
- Add management service container configuration
- Update health check configurations to use new endpoint
- Ensure proper service networking

## Implementation Files to Modify/Create

### Modified Files:
- `event-broker/app/services/queue_service.py` - Update deduplication to account+command level
- `event-processor/app/services/queue_service.py` - Add times_queued tracking, update cleanup
- `event-processor/app/utils/retry.py` - Simplify retry logic, remove exponential backoff
- `event-processor/app/config.py` - Remove unused retry config fields
- `event-processor/config/config.yaml` - Simplify retry configuration
- `event-processor/app/core/event_processor.py` - Update to use new queue methods
- `event-processor/app/commands/factory.py` - Remove health command
- `docker-compose.yaml` - Add management service
- `README.md` - Document new error handling strategy
- `failure-handling.md` - This implementation plan

### New Files:
- `management-service/` (entire directory structure)
- `management-service/app/main.py` - FastAPI application
- `management-service/app/queue_manager.py` - Queue inspection and manipulation
- `management-service/app/health.py` - Health check logic
- `management-service/requirements.txt` - Python dependencies
- `management-service/Dockerfile` - Container configuration

### Removed Files:
- `event-processor/app/commands/health_check.py` - Health command no longer needed

## Configuration Changes

### Simplified Retry Configuration (config.yaml):
```yaml
ibkr:
  connection_retry:
    max_retries: 3
    delay: 5  # Fixed delay in seconds
  order_retry:
    max_retries: 2
    delay: 1  # Fixed delay in seconds
```

### Management Service Configuration:
```yaml
management:
  api_key_header: "X-API-Key"
  redis_connection: "redis://redis:6379/0"
```

### Environment Variables:
- `MANAGEMENT_API_KEY` - API key for queue manipulation endpoints

## Deduplication Strategy
- **Event Broker**: Prevents duplicate `{account_id}:{exec_command}` combinations
- **Event Processor**: Cleans up deduplication keys on successful completion
- **Management Service**: Can view and manipulate events by account+command combination

## Health Check Strategy
- External monitoring tools can call `GET /health` on management service
- Healthy: No events with `times_queued > 1`
- Unhealthy: One or more events with `times_queued > 1`
- This provides early warning of systemic issues

## Error Handling Philosophy
1. **No Event Loss**: Events remain in queue indefinitely
2. **Command-Level Deduplication**: Only one event per account+command combination
3. **Fast Failure**: IBKR retries fail quickly to keep queue moving
4. **Visibility**: Management service provides full queue visibility
5. **Manual Control**: Operators can manipulate queue when needed
6. **Monitoring**: Health endpoint enables external monitoring integration