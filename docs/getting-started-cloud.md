# 🚀 Getting Started Guide - Cloud Deployment (Digital Ocean)

Deploy your IBKR Portfolio Rebalancer on a Digital Ocean droplet.

**You'll need:**
☁️ **Digital Ocean account** - [Sign up here](https://www.digitalocean.com/)
🔑 **SSH key pair** - for secure server access
💳 **Payment method** - droplet costs ~$12-24/month depending on size

---

## 🌐 Step 1: Create Digital Ocean Droplet

1. **Log in to Digital Ocean** and click **"Create"** → **"Droplets"**

2. **Choose configuration:**
   - **Image**: Ubuntu (Latest LTS version) x64
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
# Edit .env and accounts.yaml files as needed
docker-compose up
```

## 🌐 Step 4: Access Your Cloud Deployment

**From the server itself** (via SSH):
- **🏥 Health Status**: `curl http://localhost:8000/health`
- **📊 Queue Status**: `curl http://localhost:8000/queue/status`

**Optional - IBKR Gateway GUI Access:**
The IBKR Gateway GUI is available at `http://localhost:6080` for local troubleshooting. For remote access, consider using a reverse proxy or Cloudflare tunnel.

---

**🎉 You're Ready!** Your IBKR Portfolio Rebalancer is now running 24/7 in the cloud. **Remember to read the [Operations Guide](operations.md) for critical operational procedures before relying on it for live trading.**

*🔔 PRO TIP: Set up monitoring alerts for your droplet's resource usage in the Digital Ocean dashboard.*