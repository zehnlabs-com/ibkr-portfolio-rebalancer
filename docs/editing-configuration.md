# 📝 Editing Configuration

This guide explains how to configure your IBKR Portfolio Rebalancer by editing the `.env` and `accounts.yaml` files.

## 🔧 Environment Variables (.env)

The `.env` file contains sensitive credentials and system-wide settings. Edit this file carefully.

### Interactive Brokers Credentials

```bash
# Your IBKR username (same as TWS/IB Gateway login)
IB_USERNAME=your_ib_username

# Your IBKR password
IB_PASSWORD=your_ib_password
```

### API Keys

```bash
# API key from Zehnlabs for fetching portfolio allocations
ALLOCATIONS_API_KEY=your_allocations_api_key

# API key from Zehnlabs for real-time rebalancing events
REBALANCE_EVENT_SUBSCRIPTION_API_KEY=your_realtime_api_key
```

💡 **Get your API keys at**: [https://fintech.zehnlabs.com](https://fintech.zehnlabs.com)

### Trading Configuration

```bash
# Trading mode: "paper" for paper trading, "live" for real money
# Start with "paper" to test your setup!
TRADING_MODE=paper

# Order time in force: "DAY" or "GTC" (Good Till Canceled)
# GTC recommended for portfolio rebalancing
TIME_IN_FORCE=GTC

# Extended hours trading: "true" or "false"
# Enable if you want to trade outside regular market hours
EXTENDED_HOURS_ENABLED=false

# IBKR Gateway auto-restart time (New York timezone)
# Gateway restarts weekly at this time for stability
# You'll receive an MFA notification to authorize
AUTO_RESTART_TIME=10:00 PM
```

### Other Settings

```bash
# VNC password for accessing IB Gateway GUI (optional)
VNC_PASSWORD=password

# Log level: DEBUG, INFO, WARNING, or ERROR
LOG_LEVEL=INFO

# User notifications via ntfy.sh (mobile push notifications)
# Chose a unique name for USER_NOTIFICATIONS_CHANNEL_PREFIX
USER_NOTIFICATIONS_ENABLED=true
USER_NOTIFICATIONS_CHANNEL_PREFIX=ZLF-2025
```

## 📊 Account Configuration (accounts.yaml)

The `accounts.yaml` file defines which accounts to manage and their settings.

### Basic Structure

```yaml
accounts:
  # First account
  - account_id: "U123456"          # Your IBKR account ID
    type: paper                    # "paper" or "live"
    notification:
      channel: "etf-blend-200-35"  # Your strategy name
    rebalancing:
      cash_reserve_percent: 1.0    # Cash buffer (0-100%)

  # Second account
  - account_id: "U654321"
    type: paper
    notification:
      channel: "etf-blend-301-20"
    rebalancing:
      cash_reserve_percent: 1.0
```

### Field Descriptions

#### account_id
- Your IBKR account number
- Live accounts start with "U" (e.g., U123456)
- Paper accounts start with "DU" (e.g., DU123456)

#### type
- Must match your TRADING_MODE in .env
- `paper`: For paper trading accounts
- `live`: For real money accounts

#### notification.channel
- Your Zehnlabs strategy name
- Must be lowercase with hyphens (no spaces)
- Must match your active subscription
- Examples: `etf-blend-100-20`, `equity-growth-50-15`

#### rebalancing.cash_reserve_percent
- Percentage of equity to keep as cash buffer
- Helps handle price fluctuations during rebalancing
- Range: 0.0 to 100.0
- Recommended: 1.0 to 2.0

### IRA Account ETF Replacements

Some ETFs cannot be traded in IRA accounts due to regulations. The system automatically replaces them:

```yaml
accounts:
  - account_id: "U789012"
    type: live
    replacement_set: ira    # Enable IRA replacements
    notification:
      channel: "etf-blend-200-35"
    rebalancing:
      cash_reserve_percent: 1.0

# Replacement rules (already configured)
replacement_sets:
  ira:
    - source: UVXY
      target: VXX
      scale: 1.5    # 1 UVXY = 1.5 VXX equivalent
```

## ✅ Configuration Checklist

Before starting the services:

1. **In .env:**
   - [ ] Set your IBKR username and password
   - [ ] Add both Zehnlabs API keys
   - [ ] Choose paper or live trading mode
   - [ ] Review time-in-force and extended hours settings

2. **In accounts.yaml:**
   - [ ] Add all your IBKR account IDs
   - [ ] Set correct account types (paper/live)
   - [ ] Enter valid strategy names (channels)
   - [ ] Configure cash reserve percentages
   - [ ] Add `replacement_set: ira` for IRA accounts if needed

3. **Verify:**
   - [ ] Account types match TRADING_MODE
   - [ ] Strategy names match your Zehnlabs subscriptions
   - [ ] No sensitive information is exposed

## 🚨 Common Mistakes

1. **Wrong trading mode**: Ensure account `type` matches `TRADING_MODE`
2. **Invalid strategy names**: Must be lowercase with hyphens
3. **Missing/Incorrect API keys**: Both API keys are required

Need help? Check the [Troubleshooting Guide](../troubleshooting.md) or [create an issue](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/issues).