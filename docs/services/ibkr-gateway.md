# IBKR Gateway Service

## Overview

The IBKR Gateway service provides the connection to Interactive Brokers for trade execution. We use the third-party Docker image **`gnzsnz/ib-gateway`** which containerizes the Interactive Brokers Gateway with VNC access.

## Official Documentation

For complete documentation on the IBKR Gateway Docker image, please refer to:
- **[gnzsnz/ib-gateway on Docker Hub](https://hub.docker.com/r/gnzsnz/ib-gateway)**
- **[GitHub Repository: gnzsnz/ib-gateway](https://github.com/gnzsnz/ib-gateway)**

## Our Integration

### Configuration in Our System

We configure the IBKR Gateway through environment variables in your `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `IB_USERNAME` | Interactive Brokers username | Required |
| `IB_PASSWORD` | Interactive Brokers password | Required |
| `TRADING_MODE` | `paper` or `live` trading | `paper` |
| `VNC_PASSWORD` | VNC access password | `password` |

### Key Integration Points

- **Event Processor**: Connects to IBKR Gateway on port 4001 for trade execution
- **VNC Access**: Available through NoVNC web interface for troubleshooting  
- **Trading Mode**: Automatically configured based on `TRADING_MODE` environment variable

## VNC Troubleshooting Access

For troubleshooting IBKR Gateway issues, access the GUI through:
- **NoVNC Web Interface**: Navigate to `http://localhost:6080` 
- **Common Use Cases**: Manual login, 2FA handling, gateway configuration

See [Infrastructure Services](infrastructure.md#novnc-web-access) for detailed NoVNC usage.

## Service Dependencies

Our system waits for IBKR Gateway to complete its login process before starting dependent services:
- **Health Check**: 60-second startup delay to complete authentication  
- **Event Processor**: Waits for IBKR Gateway health check before connecting

## Common Troubleshooting

### Service Issues
```bash
# Check IBKR Gateway status
docker-compose ps ibkr

# View gateway logs  
docker-compose logs -f ibkr

# Access GUI for manual troubleshooting
# Open http://localhost:6080 in browser
```

### Integration Issues
- **API Connection**: Ensure gateway completes login (wait 60+ seconds after start)
- **Event Processor**: Check logs for IBKR connection errors
- **VNC Access**: Use NoVNC at `http://localhost:6080` for direct troubleshooting

For detailed troubleshooting of the IBKR Gateway itself, please refer to the [official documentation](https://github.com/gnzsnz/ib-gateway).

## ⚠️ Weekly Restart & MFA Requirements

**CRITICAL OPERATIONAL REQUIREMENT:**

- **Every Sunday after 01:00 ET**: IBKR Gateway automatically restarts  
- **User Action Required**: You MUST approve MFA on IBKR Mobile app within 3 minutes
- **Weekly Pattern**: Authentication needed only once per week (Sunday), then runs automatically
- **MFA Method**: Only IBKR Key (Mobile app) supported - SMS MFA will not work

**Missing MFA approval will cause trading disruption until you authenticate!**

## ⚠️ Single Login Limitation

**CRITICAL**: IBKR allows only **ONE active login session** per account:

- **Cannot use IBKR Client Portal or TWS** while automated system is running
- **Manual login will disconnect the automated system** causing trade failures
- **Especially critical during last hour before market close** when rebalance events typically occur
- **Failed trades will automatically retry** once you log out of IBKR
- **Use IBKR Mobile app sparingly** - may cause brief disconnections

## Security & Trading Modes

⚠️ **Important**: Always start with `TRADING_MODE=paper` for testing. Only switch to live trading after thorough validation.

For security best practices and detailed configuration options, see the [gnzsnz/ib-gateway documentation](https://hub.docker.com/r/gnzsnz/ib-gateway).