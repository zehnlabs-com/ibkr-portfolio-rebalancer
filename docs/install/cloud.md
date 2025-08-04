# 🚀 Installation - Cloud Deployment (DigitalOcean)

Deploy your IBKR Portfolio Rebalancer with one click on DigitalOcean!

## Prerequisites

Before you begin, you'll need:
- ✅ **DigitalOcean account** - [Sign up here](https://www.digitalocean.com/)
- 💳 **Payment method added** to your DigitalOcean account

## Quick Deploy

### Step 1: Create Your Droplet

Click the button below to deploy a pre-configured droplet:

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/droplets/new?appId=195049442&size=s-2vcpu-2gb&region=nyc3&image=docker-20-04&type=applications)

When the DigitalOcean page opens:
1. **Enter a root password** - Save this password securely!
2. **Keep all other defaults** (region, size, etc.)
3. **Click "Create Droplet"**

Wait 1-2 minutes for your droplet to fully start.

### Step 2: Install Tabby Terminal and Connect to Your Droplet

#### Install Tabby Terminal
You can use another SSH client of your choice, if you so prefer. 

1. **Download Tabby** from [https://tabby.sh](https://tabby.sh)
   - Available for Windows, macOS, and Linux
   - Choose the installer for your operating system

2. **Install and launch Tabby**

#### Set Up SSH Connection with Port Forwarding

1. **Open Tabby** and click the **Settings** button (gear icon)

2. **Navigate to** "Profiles & connections" → "New profile" and select "SSH"

3. **Configure the SSH profile:**
   - **Name:** `IBKR Portfolio Rebalancer`
   - **Host:** `YOUR_DROPLET_IP` (replace with your droplet's IP)
   - **Password:** `YOUR_DROPLET_PASSWORD` (replace with your droplet's password)   

4. **Set up port forwarding** (click "Ports" tab):
   - **Add Port Forward #1:**
     - Local port: `8000`
     - Remote host: `127.0.0.1`
     - Remote port: `8000`
   - **Add Port Forward #2:**
     - Local port: `8080`
     - Remote host: `127.0.0.1`
     - Remote port: `8080`

5. **Save the profile** and connect to your droplet

### Step 3: Run the Setup Script

Execute the automated setup script in your SSH terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/refs/heads/main/setup.sh | sudo bash
```

This script will:
- Install all required dependencies
- Set up Docker containers
- Provide you with next steps

### Step 4: Configure Your Installation

The setup script will:
- Clone the repository
- Set up configuration files
- Show you documentation links
- **Wait for you to edit the configuration files**

When the script pauses and asks you to edit the configuration files:

#### Open a Second SSH Connection to Edit Files

1. **Keep your current Tabby tab open** (where the setup script is waiting)

2. **Open a new tab in Tabby**:
   - Click the `+` button or press `Ctrl+Shift+T`
   - Select your saved SSH profile to connect again

3. **In the new tab, navigate to the project directory**:
   - Type: `cd /home/docker/zehnlabs/ibkr-portfolio-rebalancer`
   - Press `Enter`

#### Edit Files Using Nano

4. **Edit the environment variables file**:
   - Type: `nano .env`
   - Edit your environment variables
   - Press `Ctrl+O` to save
   - Press `Ctrl+X` to exit nano

5. **Edit the accounts configuration**:
   - Type: `nano accounts.yaml`
   - Configure your IBKR account(s) and strategies
   - Press `Ctrl+O` to save
   - Press `Ctrl+X` to exit nano

6. **Return to your first tab** (where the setup script is waiting)

7. **Press ENTER** to continue the installation

5. The script will then:
   - Start all Docker containers
   - Verify services are running
   - Provide access URLs

### Step 5: Access Your Services

Once setup completes, you can access:

- **📊 Container management / Log Viewer**: http://localhost:8080
  - Real-time logs from all services
  - Start/stop containers
  - Search and filter logs

- **🔧 Management API**: http://localhost:8000
  - Health checks
  - Queue status
  - System monitoring

💡 **Remember:** Your Tabby SSH connection with port forwarding must remain open to access these services.


## Post-Installation

### Notifications

Set up real-time notifications on your phone and desktop:
- Follow the guide: [User Notifications Setup](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/blob/main/docs/user-notifications.md)

## Troubleshooting

### Cannot connect via SSH
- Verify the droplet IP address in DigitalOcean dashboard
- Check if the droplet is running

## Support

- 📖 [Full Documentation](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer)
- 🐛 [Report Issues](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/issues)
- 💬 [Community Support](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/discussions)

---

**Next Steps**: After installation, refer to the [Operations Guide](../operations.md) for daily usage and the [Troubleshooting Guide](../troubleshooting.md) for common issues.