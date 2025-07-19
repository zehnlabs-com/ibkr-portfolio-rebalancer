# Development

## Local Development

### Install Dependencies

Install dependencies for each service:

```bash
# Event Broker
cd event-broker && pip install -r requirements.txt

# Event Processor
cd event-processor && pip install -r requirements.txt

# Management Service
cd management-service && pip install -r requirements.txt
```

### Run Services

Run the services (in separate terminals):

```bash
# Event Broker
cd event-broker && python -m app.main

# Event Processor  
cd event-processor && python main.py

# Management Service
cd management-service && python -m app.main
```

### Test the System

```bash
# Check system health
curl http://localhost:8000/health

# Add a test event
curl -H "Content-Type: application/json" \
  -d '{"account_id": "DU123456", "exec_command": "print-rebalance", "data": {"exec": "print-rebalance"}}' \
  http://localhost:8000/queue/events
```

## Docker Development

### Start Services

```bash
docker-compose up -d
```

### Check Logs

```bash
# All services
docker-compose logs -f

# Specific services
docker-compose logs -f event-broker
docker-compose logs -f event-processor
docker-compose logs -f management-service
```

### Verify System Health

```bash
# Check management service health
curl http://localhost:8000/health

# Check queue status
curl http://localhost:8000/queue/status
```