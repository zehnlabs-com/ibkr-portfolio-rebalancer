# Interactive Brokers Event Processor

A Docker-based event processing system that connects to Interactive Brokers Gateway for automated trading operations.

## Overview

This project provides a containerized solution for connecting to Interactive Brokers using their API through Docker. It consists of two main services:
- **IBKR Gateway**: Interactive Brokers Gateway running in a container
- **Event Processor**: Python application that connects to the IB API for processing trading events

## Prerequisites

- Docker and Docker Compose
- Interactive Brokers account (paper or live trading)
- IB Gateway credentials

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd ibkr-zehnlabs
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your IB credentials
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f event-processor
   ```

## Configuration

### Environment Variables (.env file)

#### Interactive Brokers Account Configuration
```bash
# Your IB username and password
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# Trading mode: paper or live (port automatically set: 4004 for paper, 4003 for live)
TRADING_MODE=paper

# VNC Configuration (for debugging Gateway GUI)
VNC_PASSWORD=password

# Application Configuration
LOG_LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR
```

## Important Connection Settings

### Port Configuration
The IBKR Gateway uses **socat** for port forwarding:
- **Paper Trading**: External port 4002 → Internal socat port **4004**
- **Live Trading**: External port 4001 → Internal socat port **4003**

**⚠️ Critical**: Always connect to the **socat ports** (4003/4004), not the advertised ports (4001/4002).

### API Settings
The following environment variables are automatically configured in docker-compose.yml:
- `READ_ONLY_API=no` - Enables trading functionality (not just read-only)
- `TWS_USERID_PAPER` and `TWS_PASSWORD_PAPER` - Paper trading credentials
- `TRADING_MODE=paper` - Sets trading mode

## Switching Between Paper and Live Trading

### For Paper Trading (Default)
```bash
# .env file
TRADING_MODE=paper

# Uses paper trading credentials
# Automatically connects to socat port 4004
```

### For Live Trading
```bash
# .env file
TRADING_MODE=live

# Uses live trading credentials
# Automatically connects to socat port 4003
```

**⚠️ Warning**: Live trading involves real money. Always test thoroughly with paper trading first.

## Service Architecture

### IBKR Gateway Service
- **Image**: `gnzsnz/ib-gateway:latest`
- **Ports**: 
  - `4001:4001` - Live trading API
  - `4002:4002` - Paper trading API  
  - `5900:5900` - VNC server (for GUI access)
- **Features**:
  - Automated login via IBC
  - Paper and live trading support
  - VNC access for debugging

### Event Processor Service
- **Build**: Custom Python container
- **Dependencies**: Waits for IBKR Gateway to start
- **Features**:
  - Connects to IB API using ib-insync
  - Retrieves account information
  - Processes trading events
  - Comprehensive logging

## Troubleshooting

### Connection Issues

1. **Connection Timeout**:
   - Wait for IBKR Gateway to fully initialize (60-90 seconds)
   - Check that `READ_ONLY_API=no` is set
   - Verify correct port (4003 for live, 4004 for paper)

2. **Login Failed**:
   - Verify credentials in `.env` file
   - Ensure account is not logged in elsewhere
   - Check if 2FA is properly configured

3. **API Not Available**:
   - Check IBKR Gateway logs: `docker-compose logs ibkr`
   - Look for "Login has completed" and "Configuration tasks completed"
   - Verify "Read-Only API checkbox is now set to: false"

### Monitoring

**Check service status**:
```bash
docker-compose ps
```

**View logs**:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs ibkr
docker-compose logs event-processor

# Follow logs
docker-compose logs -f event-processor
```

**Debug via VNC**:
```bash
# Access IBKR Gateway GUI at localhost:5900
# Password: value of VNC_PASSWORD from .env
```

### Expected Log Messages

**Successful IBKR Gateway startup**:
```
IBC: Login has completed
IBC: Configuration tasks completed  
Read-Only API checkbox is now set to: false
API_PORT set to: 4002
SOCAT_PORT set to: 4004
```

**Successful Event Processor connection**:
```
Successfully connected to IB Gateway at ibkr:4004
Account has X positions
Event processor initialized successfully
```

## File Structure

```
ibkr-zehnlabs/
├── docker-compose.yml          # Main service configuration
├── .env                        # Environment variables (create from .env.example)
├── .env.example               # Template for environment variables
├── event-processor/           # Event processor service
│   ├── Dockerfile            # Python container definition
│   ├── main.py              # Main application logic
│   ├── requirements.txt     # Python dependencies
│   ├── config/             # Configuration files
│   └── logs/               # Application logs
└── README.md                 # This file
```

## Security Notes

- Never commit real credentials to version control
- Use strong passwords for IB accounts
- Consider using Docker secrets for production deployments
- The VNC port (5900) should not be exposed in production

## Development

### Adding New Features
1. Modify `event-processor/main.py` for application logic
2. Update `requirements.txt` for new Python dependencies
3. Rebuild container: `docker-compose build event-processor`

### Testing
- Always test with paper trading first
- Monitor logs during development
- Use VNC access to debug IB Gateway issues

## Support

For issues related to:
- **IB Gateway Docker image**: [gnzsnz/ib-gateway-docker](https://github.com/gnzsnz/ib-gateway-docker)
- **Interactive Brokers API**: [IB API Documentation](https://interactivebrokers.github.io/tws-api/)
- **ib-insync library**: [ib-insync Documentation](https://ib-insync.readthedocs.io/)