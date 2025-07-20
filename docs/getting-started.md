# 🚀 Getting Started Guide

Choose your platform to get your IBKR Portfolio Rebalancer up and running quickly.

> ⚠️ **Critical**: Read the [Operations Guide](operations.md) to understand weekly MFA requirements and login limitations before going live.

## 🖥️ Choose Your Platform

Select the guide that matches your operating system:

### 🪟 Windows
**[Getting Started - Windows](getting-started-windows.md)**
- Windows 10/11 with WSL2 and Docker Desktop
- Step-by-step PowerShell/Command Prompt instructions
- Includes WSL2 setup and Docker Desktop configuration

### 🍎 macOS
**[Getting Started - macOS](getting-started-mac.md)**
- macOS with Docker Desktop
- Terminal-based setup instructions
- Homebrew package manager integration

### 🐧 Linux
**[Getting Started - Linux](getting-started-linux.md)**
- Ubuntu, CentOS, Fedora, Arch Linux support
- Native Docker and Docker Compose installation
- Distribution-specific package management

### ☁️ Cloud Deployment
**[Getting Started - Cloud](getting-started-cloud.md)**
- 24/7 remote operation on Digital Ocean droplets
- Complete server setup and security hardening
- Remote monitoring and backup strategies

---

## ✅ Prerequisites (All Platforms)

Before starting, ensure you have:

🏦 **IBKR Pro account** with API access enabled  (IBKR Lite won't work)
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products`  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for weekly authentication  
🎯 **Zehnlabs strategy subscription** - active subscription to Tactical Asset Allocation strategies  
🔑 **ZehnLabs API keys** - get them from Telegram bot `@FintechZL_bot` (send `/api`)  

---

## 🔧 What You'll Install

All platform guides will help you install:

- **Git** - Version control system to download the repository
- **Docker** - Containerization platform to run the application
- **Docker Compose** - Tool for running multi-container applications

---

## 🌐 Universal Access Points

After setup, you'll have access to these endpoints:

**Local Deployment (Windows/macOS/Linux):**
- **🏥 Health Status**: `http://localhost:8000/health`
- **📊 Queue Status**: `http://localhost:8000/queue/status`
- **🖥️ IBKR Gateway GUI**: `http://localhost:6080` (for troubleshooting)

**Cloud Deployment:**
- **🏥 Health Status**: `curl http://localhost:8000/health` (from server via SSH)
- **📊 Queue Status**: `curl http://localhost:8000/queue/status` (from server via SSH)
- **🖥️ IBKR Gateway GUI**: Temporarily accessible at `http://YOUR_DROPLET_IP:6080` (requires opening firewall port and strong VNC password)

---

## 🔄 Staying Updated

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

## 🤔 Which Option Should I Choose?

**Local Deployment** (Windows/macOS/Linux):
- ✅ **Best for**: Testing, development, personal use
- ✅ **Pros**: Easy setup, no additional costs, full control
- ❌ **Cons**: Computer must stay on 24/7, depends on home internet

**Cloud Deployment**:
- ✅ **Best for**: Production use, 24/7 trading, reliability
- ✅ **Pros**: Always online, professional infrastructure, remote access
- ❌ **Cons**: Monthly cost (~$12-24), requires basic server knowledge

---

## ❌ Need Help?

If you encounter issues:

1. **Check the platform-specific troubleshooting sections** in your chosen guide
2. **Review the [Troubleshooting Guide](troubleshooting.md)** for common issues
3. **Set `LOG_LEVEL=DEBUG`** in your `.env` file for detailed logging

---

# 📚 Essential Reading

## 🚨 **MUST Read:**
- **[Operations Guide](operations.md)** - Critical weekly procedures and login restrictions
- **[Remote Monitoring](monitoring.md)** - (Optional) Monitoring and alerts 

## ❌ Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

## 📖 **System Understanding:**
- **[Architecture Guide](architecture.md)** - How the system works
- **[Rebalancing Algorithm](rebalancing.md)** - Trading logic and cash management

---

**🎉 Ready to get started?** Click on your platform-specific guide above and follow the step-by-step instructions!