# 🚀 Getting Started Guide - Windows

Get your IBKR Portfolio Rebalancer up and running on Windows with WSL2 and Docker Desktop.

---

## 📥 Step 1: Install Git

Git is required to download the repository.

1. Download Git from [git-scm.com](https://git-scm.com/download/windows)
2. Run the installer with default settings
3. Verify installation by opening Command Prompt and typing: `git --version`

## 🐧 Step 2: Update WSL and Install Ubuntu

Update Windows Subsystem for Linux and install Ubuntu for optimal Docker performance.

1. **Open PowerShell or Terminal as Administrator**
2. **Update WSL**: `wsl --update`
3. **Set WSL 2 as default**: `wsl --set-default-version 2`
4. **Check if you already have Ubuntu installed**: `wsl -l -v`
   - If Ubuntu is listed, skip to step 5
   - If not, install Ubuntu: `wsl --install -d Ubuntu`
5. **Launch Ubuntu** from the Start menu and complete the initial setup if this is your first time (create username/password)

## 🐳 Step 3: Install Docker Desktop with WSL

Docker Desktop will run your rebalancing tool in containers.

1. **Download Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **During installation**, ensure **"Use WSL 2 instead of Hyper-V"** is checked
3. **After installation**, open Docker Desktop
4. **Configure WSL Integration**:
   - Go to Settings → General → Verify **"Use the WSL 2 based engine"** is enabled
   - Go to Settings → Resources → WSL Integration → Enable integration with your Ubuntu distribution
5. **Restart Docker Desktop** if needed

## 📁 Step 4: Clone the Repository

1. **Open Command Prompt or PowerShell**
2. **Create your preferred directory** e.g. `mkdir %USERPROFILE%\docker\zehnlabs`
3. **Navigate to zehnlabs directory** e.g. `cd %USERPROFILE%\docker\zehnlabs`
4. **Clone the repository**:
   ```cmd
   git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
   cd ibkr-portfolio-rebalancer
   ```

## ⚙️ Step 5: Configure Environment Variables

1. **Copy the example environment file**:
   ```cmd
   copy .env.example .env
   ```

2. **Edit the `.env` file**:
   ```cmd
   notepad .env
   ```
   💡 *(You can use any text editor of your choice)*

3. Update the values of environment variables in .env file as needed, and save the file.
   
## 🏦 Step 6: Configure Trading Accounts

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
   - Modify the data as per your IBKR trading accounts and the Zehnlabs strategies you have valid subscrptions for.

   ⚠️ **If you only want to trade one account, remove the second account section entirely. Similarly, if you want to trade more than two accounts, you can add them accordingly**

## 🚀 Step 7: Start the Application

1. **Ensure Docker Desktop is running**
2. **In your Command Prompt or PowerShell**, from the project directory, run:
   ```cmd 
   docker compose up
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

## 📋 Step 8: View Logs and Verify Successful Start

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

## 🩺 Step 9: Verify System Health

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

The Docker-based approach ensures consistent behavior across all platforms.

---

# 🔧 Common Installation Issues

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

**❌ Problems?** → See [Troubleshooting Guide](troubleshooting.md)

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now set up.

*🔔 PRO TIP: You can configure Docker Desktop to start every time you login to your computer.*


