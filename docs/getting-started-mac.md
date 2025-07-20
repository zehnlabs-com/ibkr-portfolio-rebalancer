# 🚀 Getting Started Guide - macOS

Get your IBKR Portfolio Rebalancer up and running on macOS with Docker Desktop.

---

## 📥 Step 1: Install Git

Git is required to download the repository.

1. **Install using Homebrew** (recommended):
   ```bash
   brew install git
   ```
   
   *If you don't have Homebrew, install it from [brew.sh](https://brew.sh/)*

2. **Or download from the official website**: [git-scm.com](https://git-scm.com/download/mac)

3. **Verify installation** by opening Terminal and typing: `git --version`

## 🐳 Step 2: Install Docker Desktop

Docker Desktop will run your rebalancing tool in containers.

1. **Download Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **Install the .dmg file** by dragging Docker to Applications
3. **Launch Docker Desktop** from Applications
4. **Complete the setup** - Docker will ask for system permissions
5. **Verify installation** by running in Terminal: `docker --version`

## 📁 Step 3: Clone the Repository

1. **Open Terminal**
2. **Create your preferred directory**:
   ```bash
   mkdir -p ~/docker/zehnlabs
   cd ~/docker/zehnlabs
   ```
3. **Clone the repository**:
   ```bash
   git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
   cd ibkr-portfolio-rebalancer
   ```

## ⚙️ Step 4: Configure Environment Variables

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file**:
   ```bash
   nano .env
   ```
   💡 *(You can use any text editor: `nano`, `vim`, `code`, or TextEdit)*

3. Update the values of environment variables in .env file as needed, and save the file.
   
## 🏦 Step 5: Configure Trading Accounts

1. **Copy the example accounts file**:
   ```bash
   cp accounts.example.yaml accounts.yaml
   ```

2. **Edit the accounts configuration**:
   ```bash
   nano accounts.yaml
   ```
   💡 *(You can use any text editor of your choice)*

3. **Configure your trading accounts**. 
   - Modify the data as per your IBKR trading accounts and the Zehnlabs strategies you have valid subscrptions for.

   ⚠️ **If you only want to trade one account, remove the second account section entirely. Similarly, if you want to trade more than two accounts, you can add them accordingly**

## 🚀 Step 6: Start the Application

1. **Ensure Docker Desktop is running**
2. **In Terminal**, from the project directory, run:
   ```bash
   docker compose up
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

## 📋 Step 7: View Logs and Verify Successful Start

1. **Open Docker Desktop**
2. **Go to the "Containers" tab**
3. **Find and click on your project container**
4. **After a couple of minutes, event-processor service should start**

**✅ Look for these success indicators:**
- No error messages in the logs
- Services start without crashing

**❌ If you see errors:**
- Check your `.env` file credentials
- Check your account ID
- Verify your ZehnLabs subscription is active
- Ensure Interactive Brokers account is properly set up

## 🩺 Step 8: Verify System Health

After starting the system, verify everything is working:

```bash
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

# 🔄 IMPORTANT: Staying Updated

## 🔔 Get Notified of Repository Updates

From time to time, this tool will be updated. It is IMPORTANT that you update to the latest version at your earliest convenience. To receive notifications when new versions are released:

**📺 GitHub Watch:**
1. Go to `https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer`
2. Click the **"Watch"** button
3. Select **"Custom"** → **"Releases"**
4. You'll receive email notifications for new releases

*You should schedule your updates when the markets are closed.*

## ⬆️ Update to the Latest Version

When a new version is available:

1. **Stop the running containers:**
   ```bash
   docker compose down
   ```

2. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```

3. **Rebuild and restart with the new version:**
   ```bash
   docker compose up --build -d
   ```

4. **Check logs in Docker Desktop** to ensure the update was successful

---

# 🔧 Common Installation Issues

**🐳 Docker Desktop won't start:**
- Ensure Docker Desktop has necessary system permissions
- Check Activity Monitor for any conflicting processes

**📦 Container fails to start:**
- Review Docker Desktop logs for specific error messages
- Ensure `.env` and `accounts.yaml` files exist and have correct formatting
- Set `LOG_LEVEL=DEBUG` for more detailed logging

**⚙️ Services won't start:**
- Check Docker Desktop is running
- Verify `.env` and `accounts.yaml` files exist
- Run `docker compose logs` to see error details

**❌ Problems?** → See [Troubleshooting Guide](troubleshooting.md)

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now set up.

*🔔 PRO TIP: You can configure Docker Desktop to start automatically when you log in to your Mac.*