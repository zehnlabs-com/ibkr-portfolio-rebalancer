# 🚀 Getting Started Guide

Get your IBKR Portfolio Rebalancer up and running in 4 simple steps.

> ⚠️ **Critical**: Read the [Operations Guide](operations.md) to understand weekly MFA requirements and login limitations before going live.

## ✅ Prerequisites

Before starting, ensure you have:

🏦 **IBKR Pro account** with API access enabled  
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products`  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for weekly authentication  
🎯 **Zehnlabs strategy subscription** - active subscription to Tactical Asset Allocation strategies  
🔑 **ZehnLabs API keys** - get them from Telegram bot `@FintechZL_bot` (send `/api`)  

---

## 🛠️ Step 1: Install & Configure

- **💻 Installation** → Follow the [Installation Guide](installation.md)


The Installation Guide covers: Git, WSL, Docker Desktop, repository cloning, and configuration.

---

## 🩺 Step 2: Verify Installation

After installation, check everything is working:

```bash
# Check all services are running
docker compose ps

# System should be healthy  
curl http://localhost:8000/health

# Should return: {"healthy": true, "status": "healthy"}
```

**🌐 Management Interface:**
- Health: `http://localhost:8000/health`
- Queue Status: `http://localhost:8000/queue/status` 
- IBKR GUI: `http://localhost:6080` (troubleshooting only)

**❌ Problems?** → See [Troubleshooting Guide](troubleshooting.md)

---

## 🧪 Step 3: Test with Paper Trading

**Your system starts in PAPER TRADING mode by default** - no real money at risk.

1. **Monitor logs** to see when events arrive:
   ```bash
   docker compose logs -f event-processor
   ```

2. **Check your IBKR paper account** for test trades when rebalancing events occur

3. **Verify positions and trades** match expected allocations

**Let it run for at least one full rebalancing event** before considering live trading.

---

## ✅ Step 4: Go Live (When Ready)

> ⚠️ **CRITICAL**: First read the [Operations Guide](operations.md) to understand:
> - 📅 **Weekly Sunday MFA** requirements (you MUST approve on mobile app)  
> - 🚫 **Single login limitation** (can't use IBKR web/TWS while system runs)
> - 📈 **Market close restrictions** (avoid IBKR logins in last trading hour)

### Switch to Live Trading:

1. **Edit your `.env` file:**
   ```bash
   TRADING_MODE=live  # Only after thorough paper testing!
   ```

2. **Restart the system:**
   ```bash
   docker compose restart
   ```

3. **Monitor closely** for the first few live trades

---

# 📚 Essential Reading

## 🚨 **Must Read Before Going Live:**
- **[Operations Guide](operations.md)** - Critical weekly procedures and login restrictions
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## 📖 **System Understanding:**
- **[Architecture Guide](architecture.md)** - How the system works
- **[Rebalancing Algorithm](rebalancing.md)** - Trading logic and cash management

## ⚙️ **Service Details:**
- **[Event Broker](services/event-broker.md)** - Event ingestion from Zehnlabs
- **[Event Processor](services/event-processor.md)** - Trade execution engine  
- **[Management Service](services/management-service.md)** - Monitoring API
- **[IBKR Gateway](services/ibkr-gateway.md)** - Interactive Brokers connection
- **[Infrastructure](services/infrastructure.md)** - Redis and NoVNC services

## 🔧 **Advanced Topics:**
- **[Remote Monitoring](monitoring.md)** - Cloudflare tunnels and uptime alerts
- **[Development Setup](development.md)** - Local development without Docker

---

# 🆘 Need Help?

1. **Installation issues** → [Installation Guide](installation.md) 
2. **System not working** → [Troubleshooting Guide](troubleshooting.md)
3. **Operational questions** → [Operations Guide](operations.md)
4. **Understanding the system** → [Architecture Guide](architecture.md)

---

# 🔒 Security Reminders

- **🔐 Keep `.env` file secure** - never share or commit to version control
- **🧪 Always test in paper mode first** - verify everything works before live trading
- **📊 Monitor positions regularly** - especially during first few days of operation  
- **⬆️ Keep system updated** - watch GitHub releases and update regularly

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now set up. Remember to read the [Operations Guide](operations.md) for critical operational procedures before relying on it for live trading.

> 💡 **Pro Tip**: Bookmark the [Management Interface](http://localhost:8000/health) for quick system health checks.