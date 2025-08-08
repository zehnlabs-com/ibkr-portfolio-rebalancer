# IBKR Gateway Service

## Overview

The IBKR Gateway service provides the connection to Interactive Brokers for trade execution. We use the third-party Docker image **`gnzsnz/ib-gateway`** which containerizes the Interactive Brokers Gateway.

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
- **VNC Access**: Available through external NoVNC client for troubleshooting  
- **Trading Mode**: Automatically configured based on `TRADING_MODE` environment variable

## VNC Troubleshooting Access

For troubleshooting IBKR Gateway issues, access the GUI through:
1. Navigate to https://novnc.com/noVNC/vnc.html in your browser
2. Configure WebSocket settings:
   - **Encrypt**: off
   - **Host**: 127.0.0.1
   - **Port**: 5900
3. Click **Connect** to access the IBKR Gateway interface

- **Common Use Cases**: Manual login, 2FA handling, gateway configuration

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
# Use external NoVNC client at https://novnc.com/noVNC/vnc.html
```

### Integration Issues
- **API Connection**: Ensure gateway completes login (wait 60+ seconds after start)
- **Event Processor**: Check logs for IBKR connection errors
- **VNC Access**: Use external NoVNC client at https://novnc.com/noVNC/vnc.html for gateway troubleshooting

