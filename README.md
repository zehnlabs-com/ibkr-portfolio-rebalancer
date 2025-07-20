# 📊 IBKR Portfolio Rebalancer

A portfolio rebalancing service that automatically rebalances your Interactive Brokers (IBKR) accounts based on allocations provided by Zehnlabs Tactical Asset Allocation strategies.

⚠️ **IMPORTANT DISCLAIMER**  
This software is provided "as-is" without any warranty. Automated trading involves substantial risk of loss. You are solely responsible for your trading decisions and any resulting gains or losses. This is not financial advice. Always test thoroughly and consider consulting a financial advisor before using automated trading systems.

## ✨ Features

- **🔄 Event-Driven Rebalancing**: Subscribes to real-time endpoints for rebalancing triggers
- **🏦 Multi-Account Support**: Allows multiple IBKR accounts with different strategies
- **🛡️ Robust Error Handling**: Indefinite event retention with automatic retry and queue management
- **📱 Management Service**: RESTful API for queue monitoring and manual intervention
- **🐳 Docker Support**: Containerized deployment with existing IBKR gateway

## 📚 Documentation

### 🚀 Getting Started
- **[Getting Started](docs/getting-started.md)** - Quick setup and installation guide
- **[Operations Guide](docs/operations.md)** - Critical weekly and daily operational procedures
- **[Architecture](docs/architecture.md)** - System design and service overview

### ⚙️ Service Documentation
- **[Event Broker](docs/services/event-broker.md)** - Event ingestion from Zehnlabs
- **[Event Processor](docs/services/event-processor.md)** - Trade execution and processing
- **[Management Service](docs/services/management-service.md)** - API for monitoring and control
- **[IBKR Gateway](docs/services/ibkr-gateway.md)** - Interactive Brokers connection
- **[Infrastructure](docs/services/infrastructure.md)** - Redis and NoVNC services

### 🔧 Operations & Troubleshooting  
- **[Rebalancing Algorithm](docs/rebalancing.md)** - Trading logic and cash reserves
- **[Remote Monitoring](docs/monitoring.md)** - Cloudflare tunnel and uptime alerts setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and NoVNC access
- **[Development](docs/development.md)** - Local development setup

## 🏥 System Health

Check if the system is running properly:

```bash
# System health check
curl http://localhost:8000/health

# Queue status and metrics
curl http://localhost:8000/queue/status

# View recent events
curl http://localhost:8000/queue/events?limit=10
```

## 🔄 Updates

To update to the latest version:

```bash
docker compose down
git pull origin main
docker compose up --build -d
```

## 🙏 Acknowledgments

This project builds upon many excellent open source projects. See [CREDITS.md](CREDITS.md) for full acknowledgments and licensing information.

For update notifications, watch the GitHub repository for releases.

## License

MIT License - see [LICENSE](LICENSE) file for details.