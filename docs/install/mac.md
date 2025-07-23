# 🚀 Installation - macOS

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
   docker compose up -d
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

---

**✅ Installation Complete!** Continue with the [Getting Started Guide](../getting-started.md#verify-installation) to verify your installation and next steps.

*🔔 PRO TIP: You can configure Docker Desktop to start automatically when you log in to your Mac.*