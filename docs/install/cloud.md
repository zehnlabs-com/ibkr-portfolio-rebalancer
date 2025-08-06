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

Wait a few minutes for your droplet to fully start.

### Step 2: Run the Setup Script

Execute the automated setup script in your SSH terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | sudo bash -s -- --cloud
```

This script will:
- Clone the repository
- Install all required dependencies
- Set up Docker containers
- Optionally setup Tailscale for secure remote access
- Provide you with next steps

### Step 3: Configure Your Installation

When the script pauses:

1. **Follow the complete configuration guide**: [Editing Configuration](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/blob/main/docs/editing-configuration.md)

2. **Return to your setup script** and press ENTER to continue

3. The script will then:
   - Start all Docker containers
   - Verify services are running
   - Provide access URLs

### Step 4: Access Your Services

Once setup completes, you can access:

- **📊 Container management / Log Viewer**: http://<YOUR HOST NAME>:8080
  - Real-time logs from all services
  - Start/stop containers
  - Search and filter logs

- **🔧 Management API**: http://<YOUR HOST NAME>:8000
  - Health checks
  - Queue status
  - System monitoring

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