# 🚀 Getting Started Guide - Linux

Get your IBKR Portfolio Rebalancer up and running on Linux with native Docker.

---

## 📥 Step 1: Install Git

Git is required to download the repository.

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install git
```

**CentOS/RHEL/Fedora:**
```bash
# CentOS/RHEL
sudo yum install git

# Fedora
sudo dnf install git
```

**Arch Linux:**
```bash
sudo pacman -S git
```

**Verify installation:**
```bash
git --version
```

## 🐳 Step 2: Install Docker and Docker Compose

### Ubuntu/Debian:

1. **Update package index:**
   ```bash
   sudo apt update
   ```

2. **Install Docker:**
   ```bash
   sudo apt install docker.io
   ```

3. **Install Docker Compose:**
   ```bash
   sudo apt install docker compose
   ```

4. **Start and enable Docker:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

5. **Add your user to docker group** (to run Docker without sudo):
   ```bash
   sudo usermod -aG docker $USER
   ```
   *Log out and back in for this change to take effect*

### CentOS/RHEL/Fedora:

1. **Install Docker:**
   ```bash
   # CentOS/RHEL
   sudo yum install docker docker compose
   
   # Fedora
   sudo dnf install docker docker compose
   ```

2. **Start and enable Docker:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

3. **Add your user to docker group:**
   ```bash
   sudo usermod -aG docker $USER
   ```

### Arch Linux:

1. **Install Docker:**
   ```bash
   sudo pacman -S docker docker compose
   ```

2. **Start and enable Docker:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

3. **Add your user to docker group:**
   ```bash
   sudo usermod -aG docker $USER
   ```

**Verify installation:**
```bash
docker --version
docker compose --version
```

## 📁 Step 3: Clone the Repository

1. **Open terminal**
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
   💡 *(You can use any text editor: `nano`, `vim`, `gedit`, `code`, etc.)*

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

1. **Ensure Docker service is running**:
   ```bash
   sudo systemctl status docker
   ```

2. **From the project directory, run**:
   ```bash
   docker compose up -d
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

## 📋 Step 7: View Logs and Verify Successful Start

1. **In another terminal, view running containers**:
   ```bash
   docker compose ps
   ```

2. **View logs for specific services**:
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

## 🩺 Step 8: Verify System Health

After starting the system, verify everything is working. You can use a browser to navigate to `http://localhost:8000/health` and `http://localhost:8000/queue/status` or use the command line as follows.

```bash
# System health check
curl http://localhost:8000/health

# Queue status
curl http://localhost:8000/queue/status
```

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now set up. **Remember to read the [Operations Guide](operations.md) for critical operational procedures before relying on it for live trading.**

*🔔 PRO TIP: You can set Docker to start automatically at boot with `sudo systemctl enable docker`*