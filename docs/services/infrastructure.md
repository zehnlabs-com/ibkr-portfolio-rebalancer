# Infrastructure Services

## Overview

The IBKR Portfolio Rebalancer relies on several infrastructure services that provide data persistence, remote access, and inter-service communication capabilities.

## Redis Queue System

### Purpose
Redis serves as the central message queue and caching layer for the entire system.

### Key Responsibilities
- **Event Queue**: Stores pending rebalancing events (`rebalance_queue`)
- **Active Events**: Tracks events currently being processed (`active_events_set`)
- **Retry Queue**: Manages failed events awaiting retry (`rebalance_retry_set`)
- **Delayed Execution**: Schedules events for future execution when markets closed (`delayed_execution_set`)
- **Deduplication**: Prevents duplicate events using account+command keys
- **Persistence**: Maintains data across service restarts

### Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Port** | 6379 | Standard Redis port |
| **Database** | 0 | All services use database 0 |
| **Persistence** | AOF enabled | Ensures data durability |
| **Memory** | Auto-managed | Docker handles memory allocation |

### Data Structures

**Main Queue**: `rebalance_queue` (List)
- FIFO queue of pending events ready for immediate execution
- Event Processor uses `BRPOP` for blocking dequeue
- Event Broker uses `LPUSH` (high priority) or `RPUSH` (normal priority)

**Active Events**: `active_events_set` (Set)
- Tracks `account_id:exec_command` combinations currently in progress
- Prevents duplicate processing of same account+command
- Key format: `{account_id}:{exec_command}` (e.g., "U123456:rebalance")
- Added when enqueued → Removed when completed/delayed/failed

**Retry Queue**: `rebalance_retry_set` (Sorted Set)  
- Failed events waiting for retry after delay period
- Score: Unix timestamp when event was added to retry queue
- Events older than `retry_delay_seconds` moved back to main queue
- Used for temporary failures (connection issues, etc.)

**Delayed Execution**: `delayed_execution_set` (Sorted Set)
- Events delayed due to trading hours, scheduled for future execution
- Score: Unix timestamp of when event should be executed
- Used when markets are closed - events scheduled for next market open
- Automatically moved to main queue when execution time arrives

### Health Monitoring

```bash
# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Monitor queue sizes
docker-compose exec redis redis-cli LLEN rebalance_queue
docker-compose exec redis redis-cli SCARD active_events_set
docker-compose exec redis redis-cli ZCARD rebalance_retry_set
docker-compose exec redis redis-cli ZCARD delayed_execution_set

# View queue contents (debugging)
docker-compose exec redis redis-cli LRANGE rebalance_queue 0 -1
docker-compose exec redis redis-cli SMEMBERS active_events_set
docker-compose exec redis redis-cli ZRANGE rebalance_retry_set 0 -1 WITHSCORES
docker-compose exec redis redis-cli ZRANGE delayed_execution_set 0 -1 WITHSCORES
```

### Docker Configuration

- **Image**: `redis:7-alpine` (official Redis image)
- **Persistence**: Volume mount for data durability
- **Health Check**: Redis PING command every 10 seconds
- **Restart Policy**: Always restart unless stopped
- **Network**: Internal Docker network only

## NoVNC Web Access

### Purpose
NoVNC provides web-based VNC access to the IBKR Gateway for troubleshooting and management.

### Key Features
- **Web Interface**: Access IBKR Gateway GUI through browser
- **No Client Software**: Works with any modern web browser
- **Real-time Control**: Full GUI interaction capabilities

### Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Web Port** | 6080 | HTTP access via browser |
| **VNC Target** | ibkr:5900 | Connects to IBKR Gateway VNC |
| **Access URL** | http://localhost:6080 | Direct browser access |

### Usage

**Accessing IBKR Gateway GUI:**
1. Open web browser to `http://localhost:6080`
2. Click "Connect" to establish VNC session
3. Use IBKR Gateway interface for troubleshooting

### Docker Configuration

- **Image**: `dougw/novnc:latest` (third-party NoVNC container)
- **Dependencies**: Requires IBKR Gateway to be running
- **Port Mapping**: Exposes 6080 for web access
- **Restart Policy**: Always restart unless stopped

## Docker Networking

### Network Configuration

**Network Name**: `ibkr-network`
- **Type**: Bridge network
- **Isolation**: All services communicate internally
- **External Access**: Management API (8000) and NoVNC (6080) exposed on localhost only

### Service Communication

```
┌─────────────────┐    ┌─────────────────┐
│  Event Broker   │───▶│     Redis       │
└─────────────────┘    │    (6379)       │
                       └─────────────────┘
┌─────────────────┐           ▲
│Event Processor  │───────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│  IBKR Gateway   │◀───│     NoVNC       │
│    (4001)       │    │    (6080)       │
└─────────────────┘    └─────────────────┘
         ▲
         │
┌─────────────────┐
│Management API   │
│    (8000)       │
└─────────────────┘
```

### Port Allocation

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Redis | 6379 | 127.0.0.1:6379 | Queue access |
| IBKR Gateway | 4003, 4004 | 127.0.0.1:4001, 4002 | TWS API |
| IBKR Gateway | 5900 | 127.0.0.1:5900 | VNC server |
| Management API | 8000 | 127.0.0.1:8000 | HTTP API |
| NoVNC | 8081 | 127.0.0.1:6080 | Web VNC |

## Data Persistence

### Volume Mounts

**Redis Data**: `redis_data` volume
- Persists queue data across restarts
- AOF (Append Only File) for durability

**IBKR Data**: `ib_data` volume  
- Stores IBKR Gateway settings and cache
- Login session persistence

**Application Logs**: Host directory mounts
- Service logs written to `./[service]/logs/`
- Log rotation configured (100MB max, 365 files)

