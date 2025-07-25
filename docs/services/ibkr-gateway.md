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
- **VNC Access**: Use NoVNC at `http://localhost:6080` for gateway troubleshooting

