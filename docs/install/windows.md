# 🚀 Installation - Windows

Get your IBKR Portfolio Rebalancer up and running on Windows with WSL2 and Docker Desktop. If you prefer Hyper-V over WSL you can simply skip over the WSL setps.

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

1. **Open Command Prompt** (type 'CMD' in Search)
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
   docker compose up -d
   ```

This command will:
- 📥 Download required Docker images (first run takes a few minutes)
- 🔨 Build the application containers
- ⚡ Start all services

---

**✅ Installation Complete!** Continue with the [Getting Started Guide](../getting-started.md#verify-installation) to verify your installation and next steps.

*🔔 PRO TIP: You can configure Docker Desktop to start every time you login to your computer.*


