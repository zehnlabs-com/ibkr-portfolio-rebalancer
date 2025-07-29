# 🔧 Troubleshooting Guide

## 🩺 Quick System Health Check

Start with these commands to get an overview of system status:

```bash
# Check all services are running
docker-compose ps

# Health check
curl http://localhost:8000/health

# Queue status overview
curl http://localhost:8000/queue/status
```

## 🚀 Initial Setup Issues

### 🐳 Docker Desktop Won't Start
- Ensure virtualization is enabled in BIOS/UEFI settings
- If using WSL, verify WSL 2 is properly installed and updated on Windows
- Check Docker Desktop logs for specific error messages

### Services Fail to Start
- Ensure `.env` file exists with required environment variables
- Verify `accounts.yaml` file exists and has correct data and formatting  
- Check your computer has sufficient resources (memory, disk space, CPU)
- Review service logs: `docker-compose logs [service-name]`

### Environment Configuration
- Temporarily set `LOG_LEVEL=DEBUG` in `.env` for detailed logging
- Verify all required API keys are configured
- Ensure IBKR credentials are correct in environment variables

## ⚙️ Service-Specific Issues

### 🏦 IBKR Gateway Problems

**Gateway won't log in:**
- **MOST COMMON**: Check if you need to approve IB Key MFA on IBKR Mobile app
- **SECOND MOST COMMON**: Check if you're logged into IBKR Client Portal or TWS - only one login allowed
- Access IBKR Gateway via NoVNC at `http://localhost:6080` 
- Verify IBKR account has API access enabled
- Ensure IBKR Key (Mobile app) MFA is properly configured
- Make sure your IBKR account is properly setup and has the right trading permissions

### Event Processing Issues

**Events not processing:**
- Check Event Processor is running: `docker-compose ps event-processor`
- View Event Processor logs: `docker-compose logs -f event-processor` 
- Verify IBKR Gateway connection is established
- Check Redis connectivity

**Events stuck in queue:**
- **COMMON CAUSE**: Check if you're logged into IBKR manually - events fail during login conflicts
- List problem events: `curl http://localhost:8000/queue/events?type=retry`
- Review retry counts and error messages
- Check for IBKR connectivity issues
- **Near Market Close**: Avoid manual IBKR logins during last hour of trading when rebalance events generally occur
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

# Show only retry events
curl http://localhost:8000/queue/events?type=retry
```

### Manual Queue Operations
If an event is stuck in a queue that you manually want to remove:

```bash
# Remove problematic event
curl -X DELETE http://localhost:8000/queue/events/{event-id}
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

### Temporarily Enabling Debug Logging

Modify your `.env` file:
```
LOG_LEVEL=DEBUG
```

Then restart services:
```bash
docker-compose restart
```

---

## ❌ Need Help?

If you encounter issues:

1. **Check the Common Issues above** for quick troubleshooting
2. **Community Support** Post a question to `https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/discussions`

---


