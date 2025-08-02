# 🚀 Getting Started Guide

Choose your platform to get your IBKR Portfolio Rebalancer up and running quickly.

> ⚠️ **Critical**: Read the [Operations Guide](operations.md) to understand weekly MFA requirements and login limitations.

---

## ✅ Prerequisites (All Platforms)

Before starting, ensure you have:

🏦 **IBKR Pro account** with API access enabled  (IBKR Lite won't work)  
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products` in your IBKR account  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
🚫 **Symbol Trading Verification** - Certain accounts (especially IRA accounts) do not allow all symbols to be traded. Please verify that your account allows all symbols in your respective strategies by attempting to manually buy 1 quantity of all symbols listed under the "Execution Metrics" of your chosen strategy. If certain symbols are not allowed in your account, you can specify replacement symbols in `accounts.yaml` configuration file.  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for authentication  
🎯 **Zehnlabs strategy subscription** - active subscription to [Zehnlabs Tactical Asset Allocation strategies](https://fintech.zehnlabs.com)  
🔑 **ZehnLabs API keys** - get them from Telegram bot `@FintechZL_bot` (send `/api`)  

---

> 📖 **Note**: Please note that IBKR API does not support fractional shares of ETFs. Portfolio Rebalancer automatically handles this limitation by rounding order quantities to whole numbers.

## 🖥️ Choose Your Platform

Once you have the above prerequisites, select the guide below that matches your platform. Once you have the system installed, continue with the next section below.

### 🪟 Windows (Docker Desktop)
**[Installation - Windows](install/windows.md)**
- Windows 10/11 with WSL2 and Docker Desktop (Hyper-V also works)
- Step-by-step PowerShell/Command Prompt instructions
- Includes WSL2 setup and Docker Desktop configuration

### 🍎 macOS (Docker Desktop)
**[Installation - macOS](install/mac.md)**
- macOS with Docker Desktop
- Terminal-based setup instructions
- Homebrew package manager integration

### 🐧 Linux (Docker Engine)
**[Installation - Linux](install/linux.md)**
- Ubuntu, CentOS, Fedora, Arch Linux support
- Native Docker and Docker Compose installation
- Distribution-specific package management

### ☁️ Cloud Deployment - Digital Ocean (Ubuntu)
**[Installation - Cloud](install/cloud.md)**
- Linux based cloud deployment
- Digital Ocean Droplet setup
- SSH based deployment

---

## 📋 Verify Installation

After completing the platform-specific installation, verify everything is working properly.

### View Logs and Verify Successful Start

1. **View running containers**:
   ```bash
   docker compose ps
   ```

2. **View logs for all services**:
   ```bash
   # View all logs
   docker compose logs
   
   # View logs for specific service
   docker compose logs event-processor
   ```

3. **After a couple of minutes, event-processor service should start**

**✅ Look for these success indicators:**
- No error messages in the logs
- Services start without crashing

**❌ If you see errors:**
- Check your `.env` file credentials
- Check your account ID
- Verify your ZehnLabs subscription is active
- Ensure Interactive Brokers account is properly set up

## 📋 Verify System Health

After starting the system, verify everything is working. You can use a browser to navigate to the URLs below or use the command line:

```bash
# System health check
curl http://localhost:8000/health

# Queue status
curl http://localhost:8000/queue/status
```

---

## 📱 Setup User Notifications

You can optionally configure real-time push notifications to your phone for system events. See the **[User Notifications Guide](user-notifications.md)** for complete setup instructions.

---

## 📊 Manual Rebalancing

After your containers are running, you can manually trigger rebalancing for one or all of your accounts using the following commands. This will execute orders in your brokerage accounts according to the last published allocations.

> ⚠️ **Important**: It is best to trigger manual rebalancing during market hours (RTH). When the market is closed, certain equity prices reported by the brokerage may not be accurate, causing generated orders to be miscalculated.

**🎯 Specific account:**
```bash
./tools/rebalance.sh -account U123456
```

**📋 All accounts:**
```bash
./tools/rebalance.sh -all
```

This tool reads your `accounts.yaml` configuration and attempts manual rebalance. Note that the tool will only process accounts that match the current `TRADING_MODE` setting.

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now set up. **Remember to read the [Operations Guide](operations.md) for critical operational procedures before relying on it for live trading.**

---


## 🔄 IMPORTANT: Staying Updated

From time to time, this tool will be updated. It is **IMPORTANT** that you update to the latest version at your earliest convenience.

**📺 Get Release Notifications:**
1. Go to `https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer`
2. Click **"Watch"** → **"Custom"** → **"Releases"**
3. You'll receive email notifications for new releases

**⬆️ Update Process** (all platforms):
```bash
# Stop containers
docker compose down

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose up -d --build
```

---

## 🔧 Common Installation Issues

**🐳 Docker permission denied (Linux):**
- Ensure your user is in the docker group: `sudo usermod -aG docker $USER`
- Log out and back in, or run: `newgrp docker`

**📦 Container fails to start:**
- Check Docker logs: `docker-compose logs`
- Ensure `.env` and `accounts.yaml` files exist and have correct formatting
- Temporarily set `LOG_LEVEL=DEBUG` for more detailed logging

**⚙️ Services won't start:**
- Check Docker service is running: `sudo systemctl status docker`
- Verify `.env` and `accounts.yaml` files exist
- Run `docker-compose logs` to see error details

---

## ❌ Need Help?

If you encounter issues:

1. **Check the Common Installation Issues above** for quick fixes
2. **Review the [Troubleshooting Guide](troubleshooting.md)** for comprehensive solutions
3. **Temporarily set  `LOG_LEVEL=DEBUG`** in your `.env` file for detailed logging
4. **Community Support** Post a question to `https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/discussions`

---

# 📚 Essential Reading

## 🚨 **MUST Read:**
- **[Operations Guide](operations.md)** - Critical weekly procedures and login restrictions
- **[User Notifications](user-notifications.md)** - Real-time system notifications setup
 

## ❌ Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## 📖 **System Understanding:**
- **[Rebalancing Algorithm](rebalancing.md)** - Trading logic and cash management
- **[Architecture Guide](architecture.md)** - How the system works


