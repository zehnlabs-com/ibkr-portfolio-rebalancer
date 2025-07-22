# Management Service

## Purpose

The Management Service provides a RESTful API for monitoring, and controlling the event processing system. It offers real-time visibility into queue status, event processing health, and manual queue management capabilities.

## Key Responsibilities

- **Queue Monitoring**: Real-time status of active and delayed events
- **Health Checking**: System health assessment for monitoring integrations
- **Manual Management**: Add, remove, and inspect individual events
- **Metrics Collection**: Queue statistics and processing metrics

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REDIS_URL` | Redis connection URL | No (defaults to `redis://redis:6379/0`) |
| `LOG_LEVEL` | Logging level | No (defaults to INFO) |
| `SERVICE_VERSION` | Service version for monitoring | Yes |

### Port Configuration

The service maps port **8000** for HTTP API access.

## API Endpoints

### Health Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic system health check |
| `/health/detailed` | GET | Detailed system health information |
| `/queue/status` | GET | Queue statistics and metrics |
| `/queue/events` | GET | List events with optional filtering |

### Queue Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/queue/events/{event_id}` | DELETE | Remove specific event |
| `/queue/events` | POST | Add event manually |

## API Usage Examples

### Health Monitoring

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Queue status and statistics
curl http://localhost:8000/queue/status

# List all events (default limit: 100)  
curl http://localhost:8000/queue/events

# List events with custom limit
curl http://localhost:8000/queue/events?limit=50

# List only active events
curl "http://localhost:8000/queue/events?type=active&limit=10"

# List only delayed/retry events
curl "http://localhost:8000/queue/events?type=delayed&limit=10"
```

### Manual Event Management

```bash
# Remove problematic event (replace with actual event ID)
curl -X DELETE http://localhost:8000/queue/events/5f88b639-1c1b-4e75-8114-9ed063a7fc49

# Add complete rebalance event
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "rebalance",
    "strategy_name": "strategy-name"
    
  }' \
  http://localhost:8000/queue/events

# Add dry-run event for testing
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456", 
    "exec_command": "print-rebalance",
    "eventId": "00000000-0000-0000-0000-000000000000",
    "strategy_name": "strategy-name",
    "cash_reserve_percent": 1.0
  }' \
  http://localhost:8000/queue/events
```

## Health Check Integration

The health endpoint provides system status for monitoring tools:

### Health States
- **Healthy**: No events with retries (`times_queued > 1`) and no delayed events
- **Unhealthy**: One or more events are being retried or delayed
- **Error**: Service cannot access queue or Redis is down

### Response Format
```json
{
  "healthy": true,
  "status": "healthy",
  "details": {
    "active_events": 0,
    "delayed_events": 0,
    "events_with_retries": 0
  }
}
```

## Queue Status Information

The `/queue/status` endpoint provides detailed metrics:
- Active event count
- Delayed event count  
- Events with retry attempts
- Processing rate statistics
- Redis connection status

## Integration Points

### Upstream
- **Redis Queue**: Monitors all queue types (active, delayed)
- **Event Tracking**: Accesses event retry counts and status

### Downstream
- **Monitoring Systems**: Health endpoint for uptime monitoring
- **Operators**: Manual queue management and debugging
- **CI/CD**: Health checks for deployment validation


### Monitoring Commands

```bash
# Check service health
docker-compose ps management-service

# View service logs
docker-compose logs -f management-service

# Test API connectivity
curl http://localhost:8000/health

# Monitor processing in real-time
watch -n 5 'curl -s http://localhost:8000/queue/status | jq'
```

## Docker Configuration

The service runs with:
- **Always restart** policy for high availability
- **Health checks** via curl to `/health` endpoint
- **Log rotation** (100MB max, 365 files)
- **Volume mounts** for persistent logs
- **Network access** to Redis and internal services only