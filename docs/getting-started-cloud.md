# 🚀 Getting Started Guide - Cloud Deployment (Digital Ocean)

Deploy your IBKR Portfolio Rebalancer on a Digital Ocean droplet for 24/7 operation.

> ⚠️ **Critical**: Read the [Operations Guide](operations.md) to understand weekly MFA requirements and login limitations before going live.

## ✅ Prerequisites

**IBKR Portfolio Rebalancer requirements:**
🏦 **IBKR Pro account** with API access enabled  (IBKR Lite won't work)
📊 **Trading permissions** for `Complex or Leveraged Exchange-Traded Products`  
💰 **Dividend Election** set to `Reinvest` in your IBKR account  
📱 **IBKR Key (Mobile App)** configured as MFA - **CRITICAL** for weekly authentication  
🎯 **Zehnlabs strategy subscription** - active subscription to Tactical Asset Allocation strategies  
🔑 **ZehnLabs API keys** - get them from Telegram bot `@FintechZL_bot` (send `/api`)  

**Cloud requirements:**
☁️ **Digital Ocean account** - [Sign up here](https://www.digitalocean.com/)
🔑 **SSH key pair** - for secure server access
💳 **Payment method** - droplet costs ~$12-24/month depending on size

---

## 🌐 Step 1: Create Digital Ocean Droplet

1. **Log in to Digital Ocean** and click **"Create"** → **"Droplets"**

2. **Choose configuration:**
   - **Image**: Ubuntu 22.04 LTS x64
   - **Authentication**: SSH keys (recommended) or Password

3. **Add SSH Key** (if you don't have one):
   ```bash
   # On your local machine (Windows: use Git Bash, macOS/Linux: Terminal)
   ssh-keygen -t ed25519 -C "your-email@example.com"
   
   # Display public key to copy
   cat ~/.ssh/id_ed25519.pub
   ```
   Copy the output and paste it into Digital Ocean

4. **Choose hostname**: `ibkr-rebalancer` or similar

5. **Click "Create Droplet"**

## 🔐 Step 2: Connect and Setup Server

1. **Connect to your droplet:**
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. **Update the system:**
   ```bash
   apt update && apt upgrade -y
   ```

3. **Allow SSH access:**
   ```bash
   ufw allow ssh
   ufw --force enable
   ```

## 🐳 Step 3: Install Docker and Setup Application

**From this point, follow the [Linux Getting Started Guide](getting-started-linux.md) starting from Step 2.**

The key commands are:
```bash
# Install Docker
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Clone and setup
mkdir -p ~/docker/zehnlabs
cd ~/docker/zehnlabs
git clone https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer.git
cd ibkr-portfolio-rebalancer

# Configure and start (follow Linux guide)
cp .env.example .env
cp accounts.example.yaml accounts.yaml
# Edit .env and accounts.yaml files
# IMPORTANT: Set a strong VNC password in .env if you plan to access the GUI
docker-compose up
```

## 🌐 Step 4: Access Your Cloud Deployment

**From the server itself** (via SSH):
- **🏥 Health Status**: `curl http://localhost:8000/health`
- **📊 Queue Status**: `curl http://localhost:8000/queue/status`

**Optional - IBKR Gateway GUI Access:**
If you need to access the IBKR Gateway GUI for troubleshooting:

⚠️ **Security Warning**: Only do this temporarily and ensure you have a strong VNC password set in your `.env` file.

1. **Open the VNC port temporarily:**
   ```bash
   sudo ufw allow 6080
   ```

2. **Access the GUI**: `http://YOUR_DROPLET_IP:6080`

3. **Close the port when done:**
   ```bash
   sudo ufw delete allow 6080
   ```

---

## 🔄 Updates and Maintenance

Follow the same update process as the Linux guide:

```bash
# Stop containers
docker-compose down

# Pull latest changes  
git pull origin main

# Rebuild and restart
docker-compose up --build -d
```

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now running 24/7 in the cloud. Remember to read the [Operations Guide](operations.md) for critical operational procedures.

*🔔 PRO TIP: Set up monitoring alerts for your droplet's resource usage in the Digital Ocean dashboard.*

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