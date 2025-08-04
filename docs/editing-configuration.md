# 📝 Editing Configuration

This guide explains how to configure your IBKR Portfolio Rebalancer by editing the `.env` and `accounts.yaml` files.

## 🔧 How to Edit Files on Your Server

### Open a SSH Connection

If you are running the setup script, please keep that connection open.

1. **Open a new SSH connection**:
   - **In Tabby**: Click the `+` button or press `Ctrl+Shift+T`, then select your saved SSH profile

3. **Navigate to the project directory**:
   ```bash
   cd /home/docker/zehnlabs/ibkr-portfolio-rebalancer
   ```

### Edit Files Using Nano

4. **Edit the environment variables file**:
   ```bash
   nano .env
   ```
   - Make your changes (see sections below for what to enter)
   - Press `Ctrl+O` to save
   - Press `Enter` to confirm
   - Press `Ctrl+X` to exit nano

5. **Edit the accounts configuration**:
   ```bash
   nano accounts.yaml
   ```
   - Make your changes (see sections below for what to enter)
   - Press `Ctrl+O` to save
   - Press `Enter` to confirm
   - Press `Ctrl+X` to exit nano

---

## 🔧 What to Enter: Environment Variables (.env)

The `.env` file contains sensitive credentials and system-wide settings. Edit this file carefully.

## 📊 Account Configuration (accounts.yaml)

The `accounts.yaml` file defines your IBKR accounts and what strategies they trade. You must have a valid subscription to the strategies you associate with your accounts.



### ETF Replacements

Some ETFs cannot be traded in in certain accounts. You can define replacements and link them to your accounts.



## 🚨 Common Mistakes

1. **Wrong trading mode**: Ensure account `type` matches `TRADING_MODE`
2. **Invalid strategy names**: Must be lowercase with hyphens
3. **Missing/Incorrect API keys**: Both API keys are required

Need help? Check the [Troubleshooting Guide](../troubleshooting.md) or [create an issue](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/issues).