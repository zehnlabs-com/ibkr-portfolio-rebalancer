# 🔧 Operations Guide

This guide covers critical operational requirements for running the IBKR Portfolio Rebalancer successfully. **Read this completely before going live with real trading.**

## ⚠️ Daily IBKR Gateway Restart & Weekly MFA Requirements

**This is extremely important:**

### 🔄 Daily Restart Schedule
- **IBKR Gateway automatically restarts daily**
- Daily restart time is configurable via environment variable (see below)
- **Weekly MFA approval is required** - IBKR doesn't ask for MFA for a week, so every week at restart time you'll get an MFA request

### 📱 MFA Setup Requirements
- **YOU MUST have IBKR Key (IBKR Mobile app) installed and configured**
- **YOU MUST authorize the login on your phone within 3 minutes** of the IB Key prompt
- Only IB Key (IBKR Mobile app) MFA is supported
- If you do not authorize within 3 minutes, the gateway will restart and prompt for MFA again
- Restarts will keep happening indefinitely until MFA is approved

### 📅 What to Expect
- **Every Day**: Gateway restarts automatically at the configured time
- **Weekly MFA Required**: Approximately once per week, you'll need to approve MFA on your IBKR Mobile app 

### 🛠️ Restart Time Configuration
The daily restart time is configurable. Configure the `AUTO_RESTART_TIME` environment variable in your `.env` file:

```bash
# Example: Restart at 9:00 PM America/New_York timezone
AUTO_RESTART_TIME=09:00 PM
```

**Important**: All times are in America/New_York timezone, including:
- Auto restart time configuration
- System logs timestamps
- Trading hours references
- All other time-related operations

## ⚠️ IBKR Single Login Limitation

**IBKR allows only ONE login session at a time per account:**

### 🚫 Login Conflicts
- **Cannot use IBKR Client Portal or TWS** while the automated system is running
- **Logging in manually will disconnect the automated system**
- **Failed events will be automatically retried** once you log out

### 📈 Market Close Timing (MOST IMPORTANT)
- **AVOID logging in during the LAST HOUR before market close**
- **Rebalancing events typically occur near market close**
- **Login conflicts during this time will delay critical trades**

### 🔄 Automatic Recovery
- Events that fail due to login conflicts are automatically requeued
- System will reconnect and process pending events a few minutes after you log out
- No manual intervention needed - just avoid conflicts during critical times

---

## 📋 Configuration Management

### Account Configuration Updates

When modifying the `accounts.yaml` file to add/remove accounts or change account settings, you will have to restart services. You can do so in Docker Desktop or using the following command line:

```bash
# After editing accounts.yaml, restart services to apply changes
docker compose restart
```

---

## 🏥 Health Monitoring

### Health Check
```bash
# Quick system health check
curl http://localhost:8000/health

# Detailed system health check
curl http://localhost:8000/health/detailed

# Check queue status
curl http://localhost:8000/queue/status

# View recent events
curl http://localhost:8000/queue/events?limit=10
```
---

## 🚨 Emergency Procedures

### If You Miss MFA Authorization
1. **System will keep retrying** - no immediate action needed
2. **Access NoVNC**: To check login issues you can navigate to `http://localhost:6080`
3. **Verify reconnection** via health endpoints

### If You're Logged Into IBKR During Market Close
1. **Log out immediately** from IBKR Client Portal/TWS
2. **Check delayed events**: `curl http://localhost:8000/queue/events?type=delayed`
3. **Monitor logs**: `docker-compose logs -f event-processor`
4. **Events will automatically retry** - no manual intervention needed

### System Recovery
- **Events are normally not lost** - they will retry until successful
- **System self-heals** from most connectivity issues
- **Manual intervention rarely needed** - system designed for resilience

---

See [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.