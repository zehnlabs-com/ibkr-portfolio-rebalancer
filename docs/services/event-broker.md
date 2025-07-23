# Event Broker Service

## Purpose

The Event Broker is responsible for ingesting portfolio rebalancing events from Zehnlabs and queuing them in Redis for processing. It acts as the entry point for the system, ensuring reliable event delivery and deduplication.

## Key Responsibilities

- **Event Ingestion**: Receives rebalancing events from Zehnlabs event streams
- **Queue Management**: Places events in Redis queue for downstream processing
- **Deduplication**: Prevents duplicate events using account+command combinations
- **Reliability**: Ensures no events are lost during ingestion

## Configuration

The service is configured through environment variables and a YAML configuration file:

### Account Configuration

Account settings are loaded from `accounts.yaml` at startup. **After modifying the file, restart services. You can do so in Docker Desktop or using the following command line:**

```bash
# Restart services to load new account settings
docker compose restart
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REDIS_HOST` | Redis server hostname | No (defaults to `redis`) |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No (defaults to INFO) |
| `SERVICE_VERSION` | Service version for monitoring | Yes |
| `REBALANCE_EVENT_SUBSCRIPTION_API_KEY` | API key for Zehnlabs event subscription | Yes |


## Integration Points

### Upstream
- **Zehnlabs Events**: Subscribes to rebalancing event streams using configured API key

### Downstream
- **Redis Queue**: Publishes events to `rebalance_queue` for processing
- **Active Events Set**: Maintains `active_events` set for deduplication

## Troubleshooting

### Common Issues

**Service won't start:**
- Check Redis connectivity
- Ensure `accounts.yaml` file exists and is readable

**Events not being queued:**
- Check Event Broker logs for connection errors
- Confirm Redis queue is accessible

**Duplicate events:**
- The system automatically prevents duplicates at the account+command level
- Check that account IDs are correctly configured

### Monitoring Commands

```bash
# Check service status
docker-compose ps event-broker

# View service logs
docker-compose logs -f event-broker

# Monitor Redis queue
curl http://localhost:8000/queue/status
```

## Docker Configuration

The service runs as a Docker container with:
- Automatic restart on failure
- Log rotation (100MB max, 365 files)
- Shared network access to Redis and other services
- Volume mounts for configuration and logs