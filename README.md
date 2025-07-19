# IBKR Portfolio Rebalancer

A portfolio rebalancing service that automatically rebalances your Interactive Brokers (IBKR) accounts based on allocations provided by Zehnlabs Tactical Asset Allocation strategies.

⚠️ **IMPORTANT DISCLAIMER**  
This software is provided "as-is" without any warranty. Automated trading involves substantial risk of loss. You are solely responsible for your trading decisions and any resulting gains or losses. This is not financial advice. Always test thoroughly and consider consulting a financial advisor before using automated trading systems.

## Features

- **Event-Driven Rebalancing**: Subscribes to real-time endpoints for rebalancing triggers
- **Multi-Account Support**: Allows multiple IBKR accounts with different strategies
- **Robust Error Handling**: Indefinite event retention with automatic retry and queue management
- **Management Service**: RESTful API for queue monitoring and manual intervention
- **Docker Support**: Containerized deployment with existing IBKR gateway

## Quick Start

1. **Prerequisites**: IBKR Pro account with API enabled, Docker Desktop, ZehnLabs subscription
2. **Setup**: See [Getting Started Guide](docs/getting-started.md) for complete installation instructions
3. **Start**: `docker compose up`
4. **Monitor**: `curl http://localhost:8000/health`

## Documentation

- **[Getting Started](docs/getting-started.md)** - Complete setup and installation guide
- **[Architecture](docs/architecture.md)** - System design and error handling strategy
- **[API Reference](docs/api.md)** - Management service endpoints
- **[Rebalancing Algorithm](docs/rebalancing.md)** - Trading logic and cash reserves
- **[Remote Monitoring](docs/monitoring.md)** - Cloudflare tunnel and uptime alerts setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Development](docs/development.md)** - Local development setup

## System Health

Check if the system is running properly:

```bash
# System health check
curl http://localhost:8000/health

# Queue status and metrics
curl http://localhost:8000/queue/status

# View recent events
curl http://localhost:8000/queue/events?limit=10
```

## Updates

To update to the latest version:

```bash
docker compose down
git pull origin main
docker compose up --build -d
```

For update notifications, watch the GitHub repository for releases.

## License

MIT License - see LICENSE file for details.