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

### Step 2: Connect to Your Droplet

Once your droplet is running, connect via SSH:

```bash
ssh root@YOUR_DROPLET_IP
```

Replace `YOUR_DROPLET_IP` with the public IP address shown in your DigitalOcean dashboard.

### Step 3: Run the Setup Script

Execute the automated setup script in your SSH terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/refs/heads/main/setup.sh | sudo bash
```

This script will:
- Install all required dependencies
- Set up Docker containers
- Start initial configuration services
- Provide you with next steps

### Step 4: Set Up Port Forwarding

After the script completes, you'll need to access the web interface. From your **local machine** (not the droplet), run:

```bash
ssh -L 8000:localhost:8000 -L 8080:localhost:8080 root@YOUR_DROPLET_IP
```

Keep this terminal window open while configuring.

### Step 5: Complete Configuration

1. Open your browser and navigate to: **http://localhost:8000/setup**

2. Configure your settings:
   - **Environment Variables**: Set your IBKR credentials and API keys
   - **Accounts**: Add your Interactive Brokers account(s)

3. Once both tasks show "Completed", click the **"Complete Install"** button

4. The system will restart all services (this can take a few minutes)

5. You'll be redirected to a success page with information you will need to monitor and manage your deployment.


## Post-Installation

### Accessing Your System

For ongoing access, always use SSH port forwarding:

```bash
# Port forward for web interfaces
ssh -L 8000:localhost:8000 -L 8080:localhost:8080 root@YOUR_DROPLET_IP

# Then access:
# Management: http://localhost:8000
```

## Troubleshooting

### Cannot connect via SSH
- Verify the droplet IP address in DigitalOcean dashboard
- Check if the droplet is running

### Port forwarding not working
- Ensure the SSH connection stays open
- On Windows, try using Git Bash or WSL instead of Command Prompt

## Support

- 📖 [Full Documentation](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer)
- 🐛 [Report Issues](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/issues)
- 💬 [Community Support](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/discussions)

---

**Next Steps**: After installation, refer to the [Operations Guide](../operations.md) for daily usage and the [Troubleshooting Guide](../troubleshooting.md) for common issues.