# 🚀 Getting Started Guide

Get your IBKR Portfolio Rebalancer up and running step-by-step. This guide will walk you through setting up and configuring the IBKR automated portfolio rebalancing tool for use with fintech.zehnlabs.com Tactical Asset Allocation strategies.

> ⚠️ **Before going live**: After installation, read the [Operations Guide](operations.md) to understand critical weekly restart and login requirements.

## ✅ Prerequisites

Before starting, ensure you have:

🏦 **IBKR Pro account** with API access enabled  
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products`  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for weekly authentication  
🎯 **Zehnlabs strategy subscription** - valid subscription to one or more Tactical Asset Allocation strategies  
🔑 **ZehnLabs API keys** - obtained from the Telegram bot (see below)  

## 🔑 Getting Your ZehnLabs API Keys

To retrieve your ZehnLabs API keys, use the Zehnlabs Fintech Bot on Telegram:

1. Open Telegram and search for **@FintechZL_bot**
2. Start a conversation with the bot
3. Send the command: `/api`
4. The bot will verify your account and generate your API keys

💡 **Note for first-time users:** The verification process may take a few seconds as the bot validates your account before generating your keys.

## 🛠️ Setup Options

This tool runs using Docker and can work on any operating system. You have two main options:

1. **💻 Local Setup with Docker Desktop** (Recommended - covered in this guide)
2. **☁️ Cloud Hosting** (Digital Ocean droplet, AWS, etc.)

This guide focuses on setting up locally using **Windows with WSL and Docker Desktop**. The same Docker-based setup works on macOS, Linux, and cloud environments with minor command variations.

---

# 📦 Installation and Setup

## Step 1: 📥 Install Git

Git is required to download the repository.

1. Download Git from [git-scm.com](https://git-scm.com/download/windows)
2. Run the installer with default settings
3. Verify installation by opening Command Prompt and typing: `git --version`

## Step 2: 🐧 Update WSL and Install Ubuntu

Update Windows Subsystem for Linux and install Ubuntu for optimal Docker performance.

1. **Open PowerShell or Terminal as Administrator**
2. **Update WSL**: `wsl --update`
3. **Set WSL 2 as default**: `wsl --set-default-version 2`
4. **Check if you already have Ubuntu installed**: `wsl -l -v`
   - If Ubuntu is listed, skip to step 5
   - If not, install Ubuntu: `wsl --install -d Ubuntu`
5. **Launch Ubuntu** from the Start menu and complete the initial setup if this is your first time (create username/password)

## Step 3: 🐳 Install Docker Desktop with WSL

Docker Desktop will run your rebalancing tool in containers.

1. **Download Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **During installation**, ensure **"Use WSL 2 instead of Hyper-V"** is checked
3. **After installation**, open Docker Desktop
4. **Configure WSL Integration**:
   - Go to Settings → General → Verify **"Use the WSL 2 based engine"** is enabled
   - Go to Settings → Resources → WSL Integration → Enable integration with your Ubuntu distribution
5. **Restart Docker Desktop** if needed

## Step 4: 📁 Clone the Repository

1. **Open Command Prompt or PowerShell**
2. **Create your preferred directory** e.g. `mkdir %USERPROFILE%\docker\zehnlabs`
3. **Navigate to zehnlabs directory** e.g. `cd %USERPROFILE%\docker\zehnlabs`
4. **Clone the repository**:
   ```cmd
   git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
   cd ibkr-portfolio-rebalancer
   ```

## Step 5: ⚙️ Configure Environment Variables

1. **Copy the example environment file**:
   ```cmd
   copy .env.example .env
   ```

2. **Edit the `.env` file**:
   ```cmd
   notepad .env
   ```
   💡 *(You can use any text editor of your choice)*

3. Update the following values with your actual credentials:
   ```env
   # Interactive Brokers Account Configuration
   IB_USERNAME=your_ib_username
   IB_PASSWORD=your_ib_password

   # Trading Configuration
   TRADING_MODE=paper  # Start with 'paper' for testing, change to 'live' when ready; make sure you have an IBKR paper account
   TIME_IN_FORCE=GTC   # GTC (Good Till Cancelled) or DAY
   EXTENDED_HOURS_ENABLED=true

   # API Keys
   ALLOCATIONS_API_KEY=your_allocations_api_key
   REBALANCE_EVENT_SUBSCRIPTION_API_KEY=your_realtime_api_key

   # Optional. VNC Configuration (for accessing IB Gateway GUI if needed)
   VNC_PASSWORD=choose_a_secure_password

   # Application Configuration
   LOG_LEVEL=INFO  # Use DEBUG for troubleshooting, INFO for normal operation

   # Optional. Testing account if you want to test using REST API
   TEST_ACCOUNT_ID=your_ibkr_account_id
   ```

## Step 6: 🏦 Configure Trading Accounts

1. **Copy the example accounts file**:
   ```cmd
   copy accounts.example.yaml accounts.yaml
   ```

2. **Edit the accounts configuration**:
   ```cmd
   notepad accounts.yaml
   ```
   💡 *(You can use any text editor of your choice)*

3. **Configure your trading accounts**. 

   ⚠️ **If you only want to trade one account, remove the second account section entirely.**

   **📊 Example for a single account:**
   ```yaml
   # Account 1
   ############
   - account_id: "U123456"  # Your IBKR account ID
     notification:
       # Zehnlabs strategy name: all lowercase, spaces replaced with hyphens
       # You must be subscribed to this strategy
       channel: "etf-blend-200-35"
     rebalancing:
       # Cash reserve: 0% to 10% (defaults to 1% if outside range)
       cash_reserve_percentage: 2.0
   ```

   **🏢 Example for multiple accounts:**
   ```yaml
   # Account 1
   ############
   - account_id: "U123456"
     notification:
       channel: "etf-blend-200-35"
     rebalancing:
       cash_reserve_percentage: 2.0

   # Account 2
   ############
   - account_id: "U654321"
     notification:
       channel: "etf-blend-301-20"
     rebalancing:
       cash_reserve_percentage: 2.5
   ```

## Step 7: 🚀 Start the Application

1. **Ensure Docker Desktop is running**
2. **In your Command Prompt or PowerShell**, from the project directory, run:
   ```cmd 
   docker compose up
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

## Step 8: 📋 View Logs and Verify Successful Start

1. **Open Docker Desktop**
2. **Go to the "Containers" tab**
3. **Find and click on your project container**
4. **Click on "Logs"** to view the application logs

**✅ Look for these success indicators:**
- No error messages in the logs
- Services start without crashing

**❌ If you see errors:**
- Check your `.env` file credentials
- Check your account ID
- Verify your ZehnLabs subscription is active
- Ensure Interactive Brokers account is properly set up

## Step 9: 🩺 Verify System Health

After starting the system, verify everything is working:

```bash
# Check all services are running
docker compose ps

# System health check
curl http://localhost:8000/health

# Queue status
curl http://localhost:8000/queue/status
```

**🌐 Access points:**
- **🏥 Health Status**: `http://localhost:8000/health`
- **📊 Queue Status**: `http://localhost:8000/queue/status`
- **🖥️ IBKR Gateway GUI**: `http://localhost:6080` (for troubleshooting)

---

# 🔄 Staying Updated

## 🔔 Get Notified of Repository Updates

To receive notifications when new versions are released:

**📺 GitHub Watch:**
1. Go to `https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer`
2. Click the **"Watch"** button
3. Select **"Custom"** → **"Releases"**
4. You'll receive email notifications for new releases

## ⬆️ Update to the Latest Version

When a new version is available:

1. **Stop the running containers:**
   ```cmd
   docker compose down
   ```

2. **Pull the latest changes:**
   ```cmd
   git pull origin main
   ```

3. **Rebuild and restart with the new version:**
   ```cmd
   docker compose up --build -d
   ```

4. **Check logs in Docker Desktop** to ensure the update was successful

---

# 🌐 Alternative Setups

While this guide focuses on Windows + WSL + Docker Desktop, the tool works on other platforms:

- **macOS**: Install Docker Desktop for Mac, use Terminal instead of WSL
- **Linux**: Install Docker and Docker Compose, use native terminal
- **Cloud hosting**: Deploy on Digital Ocean droplets, AWS EC2, etc.
- **Other Windows setups**: Can run without WSL using Command Prompt/PowerShell

The Docker-based approach ensures consistent behavior across all platforms.

---

# ✅ Going Live

## 🧪 Test Thoroughly in Paper Mode

- Let the system run for at least one rebalancing event
- Verify positions and trades in IBKR paper account
- Check logs for any errors or warnings

## 💰 Switch to Live Trading

Edit your `.env` file:
```bash
TRADING_MODE=live  # Only after thorough testing!
```

Restart the system:
```bash
docker compose restart
```

## ⚠️ Critical: Read Operations Guide

**Before going live**, thoroughly read the [Operations Guide](operations.md) to understand:
- 📅 Weekly Sunday MFA requirements
- 🚫 IBKR single login limitations  
- 📈 Market close timing restrictions
- 🔧 Daily monitoring procedures

---

# 🔧 Troubleshooting

## 🐛 Common Issues

**🐳 Docker Desktop won't start:**
- Ensure virtualization is enabled in BIOS/UEFI
- Verify WSL 2 is properly installed and updated

**📦 Container fails to start:**
- Review Docker Desktop logs for specific error messages
- Ensure `.env` and `accounts.yaml` files exist and have correct formatting
- Set `LOG_LEVEL=DEBUG` for more detailed logging

**⚙️ Services won't start:**
- Check Docker Desktop is running
- Verify `.env` and `accounts.yaml` files exist
- Run `docker compose logs` to see error details

**🌐 Can't access management API:**
- Ensure port 8000 isn't blocked
- Try `http://localhost:8000/health` in browser
- Check service is running: `docker compose ps management-service`

**🏦 IBKR Gateway won't connect:**
- Wait 60+ seconds for login process
- Check credentials in `.env` file
- Use NoVNC (`http://localhost:6080`) to see gateway GUI
- Ensure IBKR account has API access enabled

## 🆘 Getting More Help

1. Check the detailed logs in Docker Desktop
2. Set `LOG_LEVEL=DEBUG` in your `.env` file for verbose logging
3. Verify all prerequisites and subscriptions are active
4. Ensure firewall isn't blocking Docker or IB connections
5. Read the [Operations Guide](operations.md) and [Troubleshooting Guide](troubleshooting.md)

---

# 🔒 Security and Best Practices

- **Keep your `.env` file secure** - never share or commit it to version control
- **Start with paper trading** - use `TRADING_MODE=paper` until you're confident
- **Monitor your positions** - especially during the first few days of operation
- **Regular updates** - keep Docker images and the application updated
- **Read the [Operations Guide](operations.md)** before going live with real trading

---

**🎉 Congratulations!** Your IBKR Portfolio Rebalancer is now running. Make sure to read the [Operations Guide](operations.md) before relying on it for live trading.