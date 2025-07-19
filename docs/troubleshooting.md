# Troubleshooting

## Common Issues

### Connection Problems

#### IBKR Connection Failed
- Check IBKR gateway is running and accessible
- Verify IBKR credentials in .env file
- Ensure correct port (4004 for gateway, 7497 for TWS paper)
- Check if client ID conflicts exist

#### Redis Connection Failed
- Verify Redis service is running: `docker-compose ps redis`
- Check Redis logs: `docker-compose logs redis`
- Ensure Redis port 6379 is accessible

### Event Processing Issues

#### Events Not Processing
- Check event-processor logs: `docker-compose logs event-processor`
- Verify queue has events: `curl http://localhost:8000/queue/status`
- Check if event-processor is running: `docker-compose ps event-processor`

#### Events Stuck in Queue
- Check health status: `curl http://localhost:8000/health`
- View problematic events: `curl http://localhost:8000/queue/events`
- Check delayed events: `curl http://localhost:8000/queue/events?type=delayed`
- Check for IBKR connection issues in logs

### Management Service Issues

#### Management Service Not Accessible
- Check service is running: `docker-compose ps management-service`
- Verify port 8000 is accessible
- Check management service logs: `docker-compose logs management-service`

#### Management API Access
- Management API is internal-only and doesn't require authentication
- Ensure services are running in the same Docker network

## Queue Management

### Clear Stuck Events
```bash
# Remove specific event
curl -X DELETE http://localhost:8000/queue/events/{event-id-here}
```

### Monitor Queue Health
```bash
# Check overall system health
curl http://localhost:8000/health

# Get detailed queue status
curl http://localhost:8000/queue/status

# List events with retry counts
curl http://localhost:8000/queue/events?limit=50

# List only delayed events
curl http://localhost:8000/queue/events?type=delayed
```

### Add Event Manually
```bash
curl -H "Content-Type: application/json" \
  -d '{"account_id": "DU123456", "exec_command": "rebalance", "data": {"exec": "rebalance"}}' \
  http://localhost:8000/queue/events
```

## Logs

Check application logs for detailed error information:

```bash
# All services
docker-compose logs -f

# Specific services
docker-compose logs -f event-broker
docker-compose logs -f event-processor
docker-compose logs -f management-service

# Recent logs with timestamps
docker-compose logs -f --tail=100 -t event-processor
```

## Health Monitoring

The management service provides health endpoints for monitoring:

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed queue status
curl http://localhost:8000/queue/status

# Integration with monitoring tools
curl -s http://localhost:8000/health | jq '.healthy'
```

## Getting Started Issues

**Docker Desktop won't start:**
- Ensure virtualization is enabled in BIOS/UEFI
- Verify WSL 2 is properly installed and updated

**Container fails to start:**
- Review Docker Desktop logs for specific error messages
- Ensure `.env` and `accounts.yaml` files exist and have correct formatting
- Set `LOG_LEVEL=DEBUG` for more detailed logging

### Getting More Help

1. Check the detailed logs in Docker Desktop
2. Set `LOG_LEVEL=DEBUG` in your `.env` file for verbose logging
3. Verify all prerequisites and subscriptions are active
4. Ensure firewall isn't blocking Docker or IB connections