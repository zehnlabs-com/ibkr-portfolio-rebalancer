# Management Service API

The management service provides a RESTful API for monitoring and controlling the event queue:

## API Endpoints

**Health Monitoring**
- `GET /health` - System health check (healthy if no events with retries or delayed events)
- `GET /queue/status` - Queue statistics and metrics including delayed events
- `GET /queue/events?limit=100` - List all events (active and delayed)
- `GET /queue/events?limit=100&type=active` - List only active events
- `GET /queue/events?limit=100&type=delayed` - List only delayed events

**Queue Management**
- `DELETE /queue/events/{event_id}` - Remove specific event from queue (searches both active and delayed)
- `POST /queue/events` - Add event to queue manually

## Access

```bash
# Use with curl (no authentication needed)
curl -X DELETE http://localhost:8000/queue/events/some-event-id
```

## Health Check Integration

The health endpoint returns:
- **Healthy**: No events with `times_queued > 1` and no delayed events
- **Unhealthy**: One or more events are being retried or are in delayed queue
- **Error**: Service cannot check queue status

## Manual Event Testing

Test rebalancing by manually adding events via the management service:

```bash
# Add a dry run event
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "print-rebalance",
    "data": {"exec": "print-rebalance"}
  }' \
  http://localhost:8000/queue/events

# Add a live rebalance event
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "rebalance",
    "data": {"exec": "rebalance"}
  }' \
  http://localhost:8000/queue/events
```