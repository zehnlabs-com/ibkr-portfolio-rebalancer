# IBKR Portfolio Rebalancer

A FastAPI service for automated portfolio rebalancing using Interactive Brokers (IBKR) API. This service runs in Docker containers and supports both paper and live trading accounts.

## Features

- 🔄 Automated portfolio rebalancing based on target allocations
- 📊 Real-time portfolio position tracking
- 🧪 Paper trading support for testing
- 🚀 FastAPI with automatic API documentation
- 🐳 Docker containerized deployment
- 🔐 Secure IBKR API integration

## 📅 Weekly Schedule & 2FA Authentication

### Automated Trading Schedule

The service runs on a **weekly schedule** to provide predictable 2FA timing:

**🟢 ACTIVE PERIOD**
- **Sunday 12:00 PM ET** → **Friday 6:00 PM ET**
- Full automated trading capabilities
- Rebalancing API available

**🔴 OFFLINE PERIOD**  
- **Friday 6:00 PM ET** → **Sunday 12:00 PM ET**
- Service automatically stops (weekend break)
- No trading or API access

### What to Expect - 2FA Authentication

**📱 Every Sunday at 12:00 PM ET:**
1. **Notification**: You'll receive a push notification on your IBKR Mobile app
2. **Action Required**: Tap "Approve" within **3 minutes**
3. **Authentication**: Use Face ID/Touch ID/PIN as prompted
4. **Service Starts**: Trading service becomes active for the week

**⏱️ If You Miss the 2FA:**
- Service automatically retries every few minutes
- You'll get additional notifications until approved
- No manual intervention needed - just approve when convenient

### Before First Use - Setup Required

**📲 1. Install IBKR Mobile & Setup IB Key:**
- Download "IBKR Mobile" app (not "IB Key")
- Register for Two-Factor Authentication
- ⚠️ **Important**: Only ONE device can have IB Key active at a time

**📊 2. Request Trading Permissions:**
- **Paper Trading**: Automatically available
- **Live Trading**: Request permissions in Client Portal
- **Stock Trading**: Usually approved overnight

**🔑 3. Prepare Your Credentials:**
- Have IBKR username/password ready
- Ensure 2FA is working on your mobile device

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Interactive Brokers account (paper or live)
- IBKR Client Portal API access

### Setup

1. **Clone and navigate to the project:**
   ```bash
   git clone <your-repo-url>
   cd ibkr-portfolio-rebalancer
   ```

2. **Create environment configuration:**
   ```bash
   cp .env.example .env
   ```

3. **Configure your IBKR credentials in `.env`:**
   ```env
   IBKR_USERNAME=your_ibkr_username
   IBKR_PASSWORD=your_ibkr_password
   TRADING_MODE=paper  # or 'live' for real trading
   VNC_PASSWORD=password
   ```

4. **Start the services:**
   ```bash
   docker-compose up -d
   ```

5. **Access the services:**
   - API Documentation: http://localhost:8000/docs
   - IBKR Web Interface: http://localhost:6080 (password: `password`)
   - Health Check: http://localhost:8000/health

## API Usage

### Rebalance Portfolio

**POST** `/api/v1/rebalance`

Rebalance your portfolio to match target allocations.

**Request Body:**
```json
[
    {"symbol": "QQQ", "allocation": 0.6},
    {"symbol": "SPY", "allocation": 0.3},
    {"symbol": "VIXY", "allocation": 0.1}
]
```

**Query Parameters:**
- `execute` (boolean, default: false): Set to `true` to execute trades, `false` for dry-run

**Example (Dry Run):**
```bash
curl -X POST "http://localhost:8000/api/v1/rebalance" \
  -H "Content-Type: application/json" \
  -d '[
    {"symbol": "QQQ", "allocation": 0.6},
    {"symbol": "SPY", "allocation": 0.3},
    {"symbol": "VIXY", "allocation": 0.1}
  ]'
```

**Example (Execute Trades):**
```bash
curl -X POST "http://localhost:8000/api/v1/rebalance?execute=true" \
  -H "Content-Type: application/json" \
  -d '[
    {"symbol": "QQQ", "allocation": 0.6},
    {"symbol": "SPY", "allocation": 0.3},
    {"symbol": "VIXY", "allocation": 0.1}
  ]'
```

### Get Current Positions

**GET** `/api/v1/positions`

Retrieve current portfolio positions and total value.

```bash
curl http://localhost:8000/api/v1/positions
```

## ⚠️ IMPORTANT: Avoiding Login Conflicts

### For Daily Account Monitoring (Recommended)

**Use IBKR's Read-Only Access** to check balances without interrupting automated trading:

1. **Enable Read-Only Access in TWS:**
   - Open TWS/IB Gateway manually
   - Go to `Settings → Trading Platform → Read-Only Access`
   - Check the checkbox and click "Save"

2. **Use Read-Only Mode:**
   - When opening TWS, select "Read-Only" mode
   - View balances, positions, and market data
   - ✅ **No impact on automated rebalancing**

### For Full Trading Access

If you need to login with trading permissions:

- ⚠️ **Automated rebalancing will pause** when you login
- System automatically resumes when you logout
- **Avoid manual logins during active rebalancing**
- Check `/api/v1/positions` endpoint instead when possible

### Session Management

The service uses `secondary` session priority, meaning:
- Your manual logins take precedence
- Service gracefully yields and reconnects after you logout
- Auto-restart on 2FA timeouts for reliability

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IBKR_USERNAME` | Your IBKR username | Required |
| `IBKR_PASSWORD` | Your IBKR password | Required |
| `TRADING_MODE` | Trading mode: `paper` or `live` | `paper` |
| `VNC_PASSWORD` | Password for web interface | `password` |
| `IBKR_BASE_URL` | IBKR API base URL | `http://ibkr:5000` |

### Trading Modes

- **Paper Trading**: Use `TRADING_MODE=paper` for testing with virtual money
- **Live Trading**: Use `TRADING_MODE=live` for real money trading

⚠️ **Always test with paper trading first!**

## Development

### Project Structure

```
ibkr-portfolio-rebalancer/
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # API service container
├── requirements.txt           # Python dependencies
├── main.py                   # FastAPI application entry point
├── src/
│   ├── api/                  # API endpoints
│   │   └── rebalance.py     # Rebalancing endpoints
│   ├── models/              # Pydantic models
│   │   └── portfolio.py     # Portfolio data models
│   ├── services/            # Business logic
│   │   ├── ibkr_client.py  # IBKR API client
│   │   └── rebalancer.py   # Rebalancing logic
│   └── utils/               # Utility functions
├── logs/                    # Application logs
└── .env.example            # Environment template
```

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the API locally:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access API documentation:**
   http://localhost:8000/docs

## Updates and Maintenance

### Version Management

This project uses **version pinning** for stability and predictable deployments:

- **IBKR Docker Image**: Pinned to specific version (`10.30.1w-stable`)
- **Python Dependencies**: Pinned in `requirements.txt`
- **No automatic updates** - you control when to upgrade

**Benefits:**
- ✅ Tested, compatible combinations
- ✅ No surprise breakages from upstream changes
- ✅ Easy rollback to previous versions
- ✅ Consistent deployments across environments

### Updating the Service

#### For Users (Simple Process)

When the maintainer releases updates:

```bash
# 1. Pull latest changes
git pull origin main

# 2. Restart services with new versions
docker-compose down
docker-compose up -d --build
```

**That's it!** The maintainer has already tested the new versions for compatibility.

#### For Maintainers (Testing & Release Process)

**Before releasing updates to users:**

1. **Monitor upstream releases:**
   - Watch [extrange/ibkr-docker releases](https://github.com/extrange/ibkr-docker/releases)
   - Check Python package updates
   - Review changelogs for breaking changes

2. **Test new versions:**
   ```bash
   # Update versions in docker-compose.yml and requirements.txt
   # Test thoroughly in your environment
   docker-compose down
   docker-compose up -d --build
   
   # Verify functionality
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/positions
   # Test actual rebalancing with paper trading
   ```

3. **Release to users:**
   ```bash
   git add docker-compose.yml requirements.txt
   git commit -m "Update IBKR image to vX.X.X and dependencies"
   git push origin main
   ```

4. **Notify users:**
   - Document any breaking changes
   - Provide update instructions if different from standard process

### Version History

Current versions:
- **IBKR Docker**: `10.30.1w-stable`
- **FastAPI**: `0.104.1`
- **Last updated**: 2024-06-27

### Monitoring & Health Checks

**Service Status:**
- **API Health**: `GET /health` - Check if API is running
- **IBKR Connection**: http://localhost:6080 - Visual Gateway status
- **Weekly Schedule**: Check if it's during active hours (Sun 12PM - Fri 6PM ET)

**Container Status:**
```bash
# Check which containers are running
docker-compose ps

# View IBKR Gateway logs
docker-compose logs -f ibkr

# View API logs  
docker-compose logs -f rebalancer-api

# View scheduler logs
docker-compose logs -f scheduler
```

**Expected Container States:**
- **During Active Period**: `ibkr`, `rebalancer-api`, `scheduler` all running
- **During Offline Period**: Only `rebalancer-api`, `scheduler` running (`ibkr` stopped)
- **Sunday 12 PM ET**: `ibkr` starts automatically, expect 2FA notification

### Troubleshooting

**IBKR Connection Issues:**
1. Verify credentials in `.env` file
2. Check IBKR web interface at http://localhost:6080
3. Ensure 2FA is properly configured
4. Check container logs: `docker-compose logs ibkr`

**API Errors:**
1. Check API logs: `docker-compose logs rebalancer-api`
2. Verify portfolio has sufficient funds
3. Ensure symbols are valid and tradeable

**Common Issues:**
- Allocations must sum to exactly 1.0 (100%)
- Minimum trade size is $100
- Some symbols may not be available in paper trading

### Updating

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Rebuild and restart:**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## Security Considerations

- Never commit `.env` file to version control
- Use strong passwords for VNC access
- Regularly rotate IBKR credentials
- Monitor trading activity regularly
- Start with paper trading for testing

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify IBKR account status and permissions
3. Ensure network connectivity to IBKR servers
4. Test with paper trading first

## License

This project is for educational and personal use. Please review Interactive Brokers' terms of service before using with live accounts.

---

⚠️ **Risk Warning**: Automated trading involves financial risk. Always test thoroughly with paper trading before using live accounts. The authors are not responsible for any financial losses.


