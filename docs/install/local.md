# 🚀 Installation - Local (Docker Desktop)

Get your IBKR Portfolio Rebalancer running locally with Docker Desktop in just a few minutes.

---

## 📋 Prerequisites

Before starting, ensure you have:

### 1. **Docker Desktop Installed**
- **Windows**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL2 integration
- **macOS**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)  
- **Linux**: Install Docker Engine: `sudo apt install docker.io docker-compose` (Ubuntu/Debian)

### 2. **Git Installed**
- **Windows**: [Download Git](https://git-scm.com/download/windows)
- **macOS**: `brew install git` or [download installer](https://git-scm.com/download/mac)
- **Linux**: `sudo apt install git` (Ubuntu/Debian)

### 3. **Docker Desktop Running**
Ensure Docker Desktop is started before proceeding.

---

## ⚡ Quick Setup

### One-Command Installation

Open your terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/zehnlabs-com/ibkr-portfolio-rebalancer/main/setup.sh | bash -s -- --local
```

**That's it!** The script will:
- ✅ Check your system requirements
- ✅ Clone the repository  
- ✅ Set up configuration files
- ✅ Wait for you to edit your settings
- ✅ Start all services

### During Setup

The script will pause and show you configuration links. **Follow the configuration guide** to edit your `.env` and `accounts.yaml` files, then press ENTER to continue.

---

**Access your services:**
- 📊 **Container Management**: http://localhost:8080
- 🔧 **Management API**: http://localhost:8000

---

## ❌ Troubleshooting

**Docker not found:**
- Ensure Docker Desktop is installed and running
- Restart Docker Desktop and try again

**Services won't start:**
- Verify `.env` and `accounts.yaml` files are properly configured
- Check Docker Desktop has sufficient resources (4GB+ RAM recommended)

---

**✅ Installation Complete!** Continue with the [Getting Started Guide](../getting-started.md#verify-installation) to configure notifications and learn daily operations.