# 🔧 Troubleshooting Guide

## 🩺 Quick System Health Check

Start with these commands to get an overview of system status:

```bash
# Check all services are running
docker-compose ps

# Quick health check
curl http://localhost:8000/health

# Queue status overview
curl http://localhost:8000/queue/status
```

## 🚀 Initial Setup Issues

### 🐳 Docker Desktop Won't Start
- Ensure virtualization is enabled in BIOS/UEFI settings
- Verify WSL 2 is properly installed and updated on Windows
- Check Docker Desktop logs for specific error messages

### Services Fail to Start
- Ensure `.env` file exists with required environment variables
- Verify `accounts.yaml` file exists and has correct formatting  
- Check Docker Desktop has sufficient resources allocated
- Review service logs: `docker-compose logs [service-name]`

### Environment Configuration
- Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging
- Verify all required API keys are configured
- Ensure IBKR credentials are correct in environment variables

## ⚙️ Service-Specific Issues

### 🏦 IBKR Gateway Problems

**Gateway won't log in:**
- **MOST COMMON**: Check if it's Sunday after 01:00 ET - you need to approve MFA on IBKR Mobile app
- **SECOND MOST COMMON**: Check if you're logged into IBKR Client Portal or TWS - only one login allowed
- Access IBKR Gateway via NoVNC at `http://localhost:6080` 
- Verify IBKR account has API access enabled
- Ensure IBKR Key (Mobile app) MFA is properly configured

**API connection failures:**
- Ensure gateway completed login (wait 60+ seconds after start)
- **Weekly Restart**: If it's Sunday, approve the MFA prompt on your IBKR Mobile app
- **Login Conflict**: Log out of IBKR Client Portal/TWS if you're currently logged in
- Make sure your IBKR account is properly setup and has the right permissions

### Event Processing Issues

**Events not processing:**
- Check Event Processor is running: `docker-compose ps event-processor`
- View Event Processor logs: `docker-compose logs -f event-processor` 
- Verify IBKR Gateway connection is established
- Check Redis connectivity

**Events stuck in queue:**
- **COMMON CAUSE**: Check if you're logged into IBKR manually - events fail during login conflicts
- List problem events: `curl http://localhost:8000/queue/events?type=delayed`
- Review retry counts and error messages
- Check for IBKR connectivity issues
- **Near Market Close**: Avoid IBKR logins during last hour of trading when rebalance events occur
- Events will automatically retry once IBKR login conflicts are resolved

### Redis Connection Issues

**Redis service problems:**
- Check Redis is running: `docker-compose ps redis`
- Test connectivity: `docker-compose exec redis redis-cli ping`
- Review Redis logs: `docker-compose logs redis`


### Monitoring Queue Health

```bash
# System health overview
curl http://localhost:8000/health

# Detailed queue statistics
curl http://localhost:8000/queue/status

# List recent events
curl http://localhost:8000/queue/events?limit=20

# Show only delayed/retry events
curl http://localhost:8000/queue/events?type=delayed
```

### Manual Queue Operations

```bash
# Remove problematic event
curl -X DELETE http://localhost:8000/queue/events/{event-id}

# Add test event manually
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456", 
    "exec_command": "print-rebalance",
    "data": {"exec": "print-rebalance"}
  }' \
  http://localhost:8000/queue/events
```

## Logging and Diagnostics

### Viewing Service Logs

```bash
# All services with live updates
docker-compose logs -f

# Specific service logs
docker-compose logs -f event-processor
docker-compose logs -f event-broker
docker-compose logs -f management-service

# Recent logs with timestamps  
docker-compose logs --tail=100 -t event-processor
```

### Enabling Debug Logging

Modify your `.env` file:
```
LOG_LEVEL=DEBUG
```

Then restart services:
```bash
docker-compose restart
```

### Network Connectivity Testing

```bash
# Test inter-service connectivity
docker-compose exec event-processor nc -zv redis 6379
docker-compose exec event-processor nc -zv ibkr 4001
docker-compose exec novnc nc -zv ibkr 5900
```

