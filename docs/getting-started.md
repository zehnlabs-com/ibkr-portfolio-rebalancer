# 🚀 Getting Started Guide

Choose your platform to get your IBKR Portfolio Rebalancer up and running quickly.

> ⚠️ **Critical**: Read the [Operations Guide](operations.md) to understand weekly MFA requirements and login limitations before going live.

---

## ✅ Prerequisites (All Platforms)

Before starting, ensure you have:

🏦 **IBKR Pro account** with API access enabled  (IBKR Lite won't work)  
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products` in your IBKR account  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for authentication  
🎯 **Zehnlabs strategy subscription** - active subscription to [Zehnlabs Tactical Asset Allocation strategies](https://fintech.zehnlabs.com)  
🔑 **ZehnLabs API keys** - get them from Telegram bot `@FintechZL_bot` (send `/api`)  

---


## 🖥️ Choose Your Platform

Once you have the above prerequisites, select the guide that matches your platform:

### 🪟 Windows (Docker Desktop)
**[Getting Started - Windows](getting-started-windows.md)**
- Windows 10/11 with WSL2 and Docker Desktop
- Step-by-step PowerShell/Command Prompt instructions
- Includes WSL2 setup and Docker Desktop configuration

### 🍎 macOS (Docker Desktop)
**[Getting Started - macOS](getting-started-mac.md)**
- macOS with Docker Desktop
- Terminal-based setup instructions
- Homebrew package manager integration

### 🐧 Linux (Docker Engine)
**[Getting Started - Linux](getting-started-linux.md)**
- Ubuntu, CentOS, Fedora, Arch Linux support
- Native Docker and Docker Compose installation
- Distribution-specific package management

### ☁️ Cloud Deployment - Digital Ocean (Ubuntu)
**[Getting Started - Cloud](getting-started-cloud.md)**
- Linux based cloud deployment
- Digital Ocean Droplet setup
- SSH based deployment

---

## 🌐 Access Points (All Platforms)

After setup, you'll have access to these endpoints:

- **🏥 Health Status**: `http://localhost:8000/health`
- **📊 Queue Status**: `http://localhost:8000/queue/status`
- **🖥️ IBKR Gateway GUI**: `http://localhost:6080` (for troubleshooting)

---

## 🔄 IMPORTANT: Staying Updated

From time to time, this tool will be updated. It is IMPORTANT that you update to the latest version at your earliest convenience.

**📺 Get Notifications:**
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
docker compose up --build -d
```

---

## 🔧 Common Installation Issues

**🐳 Docker permission denied:**
- Ensure your user is in the docker group: `sudo usermod -aG docker $USER`
- Log out and back in, or run: `newgrp docker`

**📦 Container fails to start:**
- Check Docker logs: `docker-compose logs`
- Ensure `.env` and `accounts.yaml` files exist and have correct formatting
- Set `LOG_LEVEL=DEBUG` for more detailed logging

**⚙️ Services won't start:**
- Check Docker service is running: `sudo systemctl status docker`
- Verify `.env` and `accounts.yaml` files exist
- Run `docker-compose logs` to see error details

---

## ❌ Need Help?

If you encounter issues:

1. **Check the Common Installation Issues above** for quick fixes
2. **Review the [Troubleshooting Guide](troubleshooting.md)** for comprehensive solutions
3. **Set `LOG_LEVEL=DEBUG`** in your `.env` file for detailed logging

---

# 📚 Essential Reading

## 🚨 **MUST Read:**
- **[Operations Guide](operations.md)** - Critical weekly procedures and login restrictions
- **[Remote Monitoring](monitoring.md)** - Monitoring and alerts 

## ❌ Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## 📖 **System Understanding:**
- **[Architecture Guide](architecture.md)** - How the system works
- **[Rebalancing Algorithm](rebalancing.md)** - Trading logic and cash management

