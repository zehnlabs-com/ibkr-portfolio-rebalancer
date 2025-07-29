# 📊 IBKR Portfolio Rebalancer

A dockerized portfolio rebalancing service that automatically rebalances your Interactive Brokers (IBKR) accounts based on allocations provided by [Zehnlabs Tactical Asset Allocation strategies](https://fintech.zehnlabs.com).

⚠️ **IMPORTANT DISCLAIMER**  
This software is provided "as-is" without any warranty. Community support is the only available support option via [GitHub Discussions](https://github.com/zehnlabs-com/ibkr-portfolio-rebalancer/discussions). Automated trading involves substantial risk of loss. You are solely responsible for your trading decisions and any resulting gains or losses. Nothing in this repository, linked tools, services, or discussions should be considered financial advice. Always test thoroughly and consider consulting a financial advisor before using this system.

## ✨ Features

- **🐳 Docker Deployment**: OS agnostic containerized local or cloud deployment
- **🔄 Event-Driven Rebalancing**: Subscribes to real-time Zehnlabs endpoints for rebalancing triggers
- **🏦 Multi-Account Support**: Allows multiple IBKR accounts and multiple strategies
- **🛡️ Robust Error Handling**: Indefinite event retention with automatic retry and queue management
- **📱 Management Service**: RESTful API for queue monitoring and manual intervention
- **🔔 Mobile Notifications**: Real-time push notifications to your phone via ntfy.sh

## 📚 Documentation

### 🚀 Getting Started
- **[Getting Started](docs/getting-started.md)** - Detailed installation instructions  
- **[Operations Guide](docs/operations.md)** - Weekly and daily operational procedures

### ⚙️ Design and Architecture
- **[Architecture](docs/architecture.md)** - System design and service overview
- **[Event Broker](docs/services/event-broker.md)** - Event ingestion from Zehnlabs
- **[Event Processor](docs/services/event-processor.md)** - Event processing and trade execution
- **[Management Service](docs/services/management-service.md)** - API for monitoring and control
- **[IBKR Gateway](docs/services/ibkr-gateway.md)** - Interactive Brokers connection
- **[Infrastructure](docs/services/infrastructure.md)** - Redis and NoVNC services
- **[Rebalancing Algorithm](docs/rebalancing.md)** - Trading logic and cash reserves
- **[User Notifications](docs/user-notifications.md)** - Real-time system notifications via ntfy.sh

### 🔧 Development & Troubleshooting  
- **[Development](docs/development.md)** - Local development setup
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues

## 🏥 System Health

Check if the system is running properly:

```bash
# System health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

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

This project builds upon many excellent open source projects. See [CREDITS](CREDITS.md) for full acknowledgments and licensing information.

For update notifications, watch the GitHub repository for releases.

## License

MIT License - see [LICENSE](LICENSE) file for details.