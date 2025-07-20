# 🔧 Operations Guide

This guide covers critical operational requirements for running the IBKR Portfolio Rebalancer successfully. **Read this completely before going live with real trading.**

## ⚠️ Weekly IBKR Gateway Restart & MFA Requirements

**This is extremely important:**

### 🔄 Weekly Restart Schedule
- **IBKR Gateway automatically restarts every Sunday after 01:00 ET**
- **Weekly restart is an IBKR requirement that we cannot control**
- Weekly restart time can be configured (see below)
- When the gateway restarts, the user must reauthenticate MFA

### 📱 MFA Setup Requirements
- **YOU MUST have IBKR Key (IBKR Mobile app) installed and configured**
- **YOU MUST authorize the login on your phone within 3 minutes** of the IB Key prompt
- Only IB Key (IBKR Mobile app) MFA is supported

### 📅 What to Expect
- **Every Sunday**: Gateway restarts automatically around 01:00 ET
- **Your Action Required**: Approve the MFA prompt on your IBKR Mobile app within 3 minutes

### 🛠️ Restart Time Configuration
The Sunday restart time is configurable (defaults to after 01:00 ET). Configure the `AUTO_RESTART_TIME` environment variable in your `.env` file:

```bash
# Example: Restart at 2:00 AM ET instead of 1:00 AM
AUTO_RESTART_TIME=02:00 AM
```

For detailed configuration options, see the [gnzsnz/ib-gateway environment variables documentation](https://github.com/gnzsnz/ib-gateway-docker/blob/master/README.md#environment-variables).

### 🏠 Alternative: Weekend Shutdown Schedule
If the Sunday 01:00 ET MFA timing is inconvenient, you can use this alternative approach:

- **Friday Evening**: Shutdown the container stack after market close
  ```bash
  docker-compose down
  ```
- **Monday Morning**: Restart the system when you can authorize MFA on Monday morning
  ```bash
  docker-compose up -d
  ```
- **Authorize MFA**: Approve the login on your IBKR Mobile app when containers start
- **Benefits**: No late-night weekend MFA required, fresh weekly start on Monday

---

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

### 🕐 Best Practices
- **Check your positions BEFORE the last trading hour**
- **Use mobile IBKR app for quick balance checks** (may cause brief disconnection)
- **Log out immediately** if you need to access IBKR manually
- **Monitor system logs** after manual logins to ensure reconnection

### 🔄 Automatic Recovery
- Events that fail due to login conflicts are automatically requeued
- System will reconnect and process pending events once you log out
- No manual intervention needed - just avoid conflicts during critical times

---

## 🏥 Health Monitoring

### Daily Checks
```bash
# Quick system health check
curl http://localhost:8000/health

# Check queue status
curl http://localhost:8000/queue/status

# View recent events
curl http://localhost:8000/queue/events?limit=10
```

### Weekly Checklist
**For Default Sunday Schedule:**
- [ ] **01:00 ET onwards**: Watch for MFA notification on IBKR Mobile app
- [ ] **Approve MFA within 3 minutes** when prompted
- [ ] **Verify system reconnection** after MFA approval
- [ ] **Check health endpoints** to confirm system is operational

**For Weekend Shutdown Schedule:**
- [ ] **Friday Evening**: Shutdown system after market close (`docker-compose down`)
- [ ] **Monday Morning**: Start system when convenient (`docker-compose up -d`)
- [ ] **Approve MFA** when prompted on IBKR Mobile app
- [ ] **Check health endpoints** to confirm system is operational

### Warning Signs
- **Events stuck in delayed queue**: May indicate login conflicts or connectivity issues
- **Health endpoint shows unhealthy**: System needs attention
- **No events processing**: Check IBKR Gateway status and connectivity

---

## 🚨 Emergency Procedures

### If You Miss MFA Authorization
1. **System will keep retrying** - no immediate action needed
2. **Access NoVNC**: Navigate to `http://localhost:6080`
3. **Manually approve** MFA through the gateway interface
4. **Verify reconnection** via health endpoints

**Note**: This applies to both Sunday automatic restarts and manual Monday startups

### If You're Logged Into IBKR During Market Close
1. **Log out immediately** from IBKR Client Portal/TWS
2. **Check delayed events**: `curl http://localhost:8000/queue/events?type=delayed`
3. **Monitor logs**: `docker-compose logs -f event-processor`
4. **Events will automatically retry** - no manual intervention needed

### System Recovery
- **Events are never lost** - they will retry until successful
- **System self-heals** from most connectivity issues
- **Manual intervention rarely needed** - system designed for resilience

---

## 📊 Performance Optimization

### Trading Hours Awareness
- **Pre-market (4:00-9:30 ET)**: Safe time for manual IBKR access
- **Market hours (9:30-16:00 ET)**: Avoid manual IBKR access
- **Last hour (15:00-16:00 ET)**: **CRITICAL** - absolutely no manual IBKR access
- **After hours (16:00+ ET)**: Generally safe for manual access

### Resource Management
- **Monitor Docker resource usage**: `docker stats`
- **Check log file sizes**: Logs rotate automatically but monitor disk space
- **Redis memory usage**: Handled automatically but monitor for unusual growth

### Backup Considerations
- **Configuration files**: Keep backups of `.env` and `accounts.yaml`
- **Event history**: Redis data persists in Docker volumes
- **Service logs**: Automatically rotated and retained

---

## 📞 When to Seek Help

Contact support or check documentation when:
- **Consistent MFA failures** despite proper setup
- **Events repeatedly failing** with same error
- **System health consistently unhealthy** after following troubleshooting
- **Unusual trading behavior** or unexpected positions

See [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.