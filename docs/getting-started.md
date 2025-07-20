# 🚀 Getting Started Guide

Get your IBKR Portfolio Rebalancer up and running in under 30 minutes.

## Prerequisites

Before starting, ensure you have:

✅ **IBKR Pro account** with API access enabled  
✅ **IBKR Key (Mobile App)** configured for MFA authentication  
✅ **Trading permissions** for Exchange-Traded Products  
✅ **Dividend Election** set to "Reinvest"  
✅ **Zehnlabs strategy subscription** and API keys  

> ⚠️ **Important**: Before going live, read the [Operations Guide](operations.md) to understand critical weekly restart and login requirements.

## Get Your API Keys

1. Open Telegram and search for **@FintechZL_bot**
2. Send the command: `/api`
3. Save the API keys provided by the bot

## Quick Installation

### Option 1: Docker Desktop (Recommended)

1. **Install Docker Desktop** for your operating system
2. **Clone or download** this repository
3. **Copy example files**:
   ```bash
   cp .env.example .env
   cp accounts.example.yaml accounts.yaml
   ```

4. **Configure your environment** (`.env` file):
   ```bash
   # IBKR Credentials
   IB_USERNAME=your_ibkr_username
   IB_PASSWORD=your_ibkr_password
   TRADING_MODE=paper  # Start with paper trading!
   
   # Zehnlabs API Keys (from Telegram bot)
   ALLOCATIONS_API_KEY=your_allocations_key
   REBALANCE_EVENT_SUBSCRIPTION_API_KEY=your_events_key
   ```

5. **Configure your accounts** (`accounts.yaml` file):
   ```yaml
   accounts:
     - account_id: "DU123456"  # Your IBKR account ID
       notification_channel: "strategy-name"  # Your strategy name
       cash_reserve_percentage: 1.0
   ```

6. **Start the system**:
   ```bash
   docker compose up -d
   ```

### Option 2: Cloud/VPS Setup

For cloud deployment, see the [Remote Monitoring](monitoring.md) guide for Cloudflare tunnel setup.

## First Run Verification

### 1. Check System Health
```bash
# All services should be running
docker compose ps

# System should be healthy
curl http://localhost:8000/health
```

### 2. Test with Paper Trading
- System starts in **paper trading mode** by default
- Monitor logs: `docker compose logs -f event-processor`
- Events will appear when rebalancing occurs

### 3. Access Management Interface
- **Health Status**: `http://localhost:8000/health`
- **Queue Status**: `http://localhost:8000/queue/status`
- **IBKR Gateway GUI**: `http://localhost:6080` (for troubleshooting)

## Going Live

### 1. Test Thoroughly in Paper Mode
- Let the system run for at least one rebalancing event
- Verify positions and trades in IBKR paper account
- Check logs for any errors or warnings

### 2. Switch to Live Trading
Edit your `.env` file:
```bash
TRADING_MODE=live  # Only after thorough testing!
```

Restart the system:
```bash
docker compose restart
```

### 3. Critical: Read Operations Guide
**Before going live**, thoroughly read the [Operations Guide](operations.md) to understand:
- 📅 Weekly Sunday MFA requirements
- 🚫 IBKR single login limitations  
- 📈 Market close timing restrictions
- 🔧 Daily monitoring procedures

## Next Steps

### Essential Reading
- **[Operations Guide](operations.md)** - Critical weekly and daily procedures
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
- **[Architecture](architecture.md)** - How the system works

### Optional Configuration
- **[Remote Monitoring](monitoring.md)** - Cloudflare tunnels and alerts
- **[Development](development.md)** - Local development setup

## Common First-Time Issues

**Services won't start:**
- Check Docker Desktop is running
- Verify `.env` and `accounts.yaml` files exist
- Run `docker compose logs` to see error details

**Can't access management API:**
- Ensure port 8000 isn't blocked
- Try `http://localhost:8000/health` in browser
- Check service is running: `docker compose ps management-service`

**IBKR Gateway won't connect:**
- Wait 60+ seconds for login process
- Check credentials in `.env` file
- Use NoVNC (`http://localhost:6080`) to see gateway GUI
- Ensure IBKR account has API access enabled

> 💡 **Tip**: Most issues are resolved by reading the [Operations Guide](operations.md) and [Troubleshooting Guide](troubleshooting.md).

---

**🎉 Congratulations!** Your IBKR Portfolio Rebalancer is now running. Make sure to read the [Operations Guide](operations.md) before relying on it for live trading.