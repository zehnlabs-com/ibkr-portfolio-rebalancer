# IBKR Portfolio Rebalancer

An automated portfolio rebalancing service that integrates with Interactive Brokers and Ably.com for event-driven rebalancing.

## Features

- **Event-Driven Rebalancing**: Subscribes to Ably.com endpoints for real-time rebalancing triggers
- **Multi-Account Support**: Manage multiple IBKR accounts with different allocation strategies
- **Configurable Allocation APIs**: Fetch target allocations from external APIs
- **Dry-Run Mode**: Test rebalancing without executing actual trades
- **Robust Connection Management**: Automatic retry logic and graceful degradation
- **Modern IBKR Integration**: Uses ib_async (successor to ib_insync) for Interactive Brokers API
- **Docker Support**: Containerized deployment with existing IBKR gateway
- **Equity Reserve Management**: Configurable cash reserve to improve order fill rates and handle price movements

## Architecture

The application follows a modular architecture with single responsibility principle:

```
app/
├── main.py                 # Main application entry point
├── config.py              # Configuration management
├── logger.py              # Logging setup
├── cli.py                 # Command-line interface for testing
└── services/
    ├── ibkr_client.py     # IBKR connection and trading
    ├── ably_service.py    # Ably.com event subscription
    ├── allocation_service.py  # API calls for allocations
    └── rebalancer_service.py  # Core rebalancing logic
```

## Configuration

### Accounts Configuration

Edit `accounts.yaml` to configure your IBKR accounts:

```yaml
- account_id: "DU123456"
  notification:
    channel: "strategy-name-100"
  rebalancing:
    equity_reserve_percentage: 1.0  # 1% cash reserve (default)

- account_id: "DU789012"
  notification:
    channel: "strategy-name-200"
  rebalancing:
    equity_reserve_percentage: 2.5  # 2.5% cash reserve
```

The allocations URL is automatically constructed as: `{base_url}/{channel}/allocations`

### Application Configuration

Configure the allocations API base URL in `config.yaml`:

```yaml
# Allocations API Configuration
allocations:
  base_url: "https://workers.fintech.zehnlabs.com/api/v1"
```

This allows all accounts to share the same base URL while having different strategy channels.

### Environment Variables

Copy `.env.example` to `.env` for sensitive data:

```bash
# IBKR Credentials
IBKR_USERNAME=your_username
IBKR_PASSWORD=your_password
TRADING_MODE=paper

# Global API Keys (shared across all accounts)
REALTIME_API_KEY=your_ably_key
ZEHNLABS_FINTECH_API_KEY=your_allocation_key

# Application Settings
LOG_LEVEL=INFO
```

### Allocation API Format

Your allocation API should return JSON in this format:

```json
{
  "status": "success",
  "data": {
    "allocations": [
      {"symbol": "EDC", "allocation": 0.2141},
      {"symbol": "QLD", "allocation": 0.1779},
      {"symbol": "QQQ", "allocation": 0.141},
      {"symbol": "BTAL", "allocation": 0.2817},
      {"symbol": "SPXL", "allocation": 0.0368},
      {"symbol": "TQQQ", "allocation": 0.1475}
    ],
    "name": "etf-blend-301-20",
    "strategy_long_name": "ETF Blend 301-20",
    "last_rebalance_on": "2025-06-24",
    "as_of": "2025-06-24"
  }
}
```

The application will:
- Check that `status` is `"success"`
- Extract allocations from `data.allocations` array
- Log strategy information for transparency
- Validate that allocations sum to approximately 1.0

### Execution Control via Ably Payload

The application uses the Ably notification payload to determine execution mode:

**Live Execution:**
```json
{"execution": "rebalance"}
```

**Dry Run (default for safety):**
```json
{}
```
or 
```json
{"execution": "dry_run"}
```
or any other value/missing payload.

This design ensures that **dry run is the safe default** - live execution only happens when explicitly requested with the exact `"rebalance"` value.

## Usage

### Docker Deployment

1. Start the services:
```bash
docker-compose up -d
```

2. Check logs:
```bash
docker-compose logs -f portfolio-rebalancer
```

### Dry Run Testing

Test rebalancing without executing trades:

```bash
# Run dry run for first configured account
docker-compose exec portfolio-rebalancer python -m app.cli dry-run

# Run dry run for specific account
docker-compose exec portfolio-rebalancer python -m app.cli dry-run --account-id DU123456

# List configured accounts
docker-compose exec portfolio-rebalancer python -m app.cli list-accounts
```

## Rebalancing Algorithm

The rebalancer implements a standard portfolio rebalancing algorithm with equity reserve management:

1. **Fetch Target Allocations**: Calls configured API to get target percentages
2. **Get Current Positions**: Retrieves current holdings from IBKR
3. **Calculate Available Equity**: `Available Equity = Total Account Value - (Reserve % × Total Account Value)`
4. **Calculate Target Positions**: Uses available equity (not total) for allocation calculations
5. **Generate Orders**: Creates buy/sell orders to reach target allocation within available equity
6. **Execute Trades**: Submits market orders to IBKR

### Equity Reserve System

The system maintains a configurable cash reserve to improve order fill rates and handle market volatility:

**Purpose:**
- **Improved Fill Rates**: Market orders are more likely to fill when there's a cash buffer for price movements
- **Settlement Buffer**: Provides cushion for trade settlement and fees
- **Risk Management**: Prevents over-leveraging the account

**Configuration:**
Each account can have its own reserve percentage configured in `accounts.yaml`:

```yaml
- account_id: "DU123456"
  rebalancing:
    equity_reserve_percentage: 1.0  # 1% reserve (default)
```

**Validation:**
- **Range**: 0% to 10% (values outside this range default to 1%)
- **Default**: 1% if not specified or invalid
- **Logging**: Invalid values are logged with warnings

**Example:**
- Account Value: $100,000
- Reserve: 2% 
- Available for Trading: $98,000
- Cash Reserve: $2,000

### API Response

The dry run and live rebalancing API responses now include detailed equity information:

```json
{
  "account_id": "DU123456",
  "execution_mode": "dry_run",
  "equity_info": {
    "total_equity": 100000.00,
    "reserve_percentage": 1.0,
    "reserve_amount": 1000.00,
    "available_for_trading": 99000.00
  },
  "orders": [
    {
      "symbol": "AAPL",
      "quantity": 10,
      "action": "BUY",
      "market_value": 1500.00
    }
  ],
  "status": "success",
  "message": "Dry run rebalancing completed successfully",
  "timestamp": "2023-12-01T10:00:00Z"
}
```

This approach solves the original problem where orders might not fill due to price movements between calculation and execution, by ensuring sufficient cash reserves and using total equity calculations instead of precise share quantities.

### Key Features:
- Handles fractional shares by rounding to nearest whole share
- Sells positions not in target allocation
- Only trades when difference exceeds 0.5 shares
- Supports dry-run mode for testing

## Event Flow

1. Ably.com publishes rebalance event to configured channel
2. Application receives event for specific account
3. Parses payload to determine execution mode:
   - `{"execution": "rebalance"}` → Live execution
   - No payload or other values → Dry run (safe default)
4. Calls allocation API to get target percentages
5. Calculates required trades
6. Executes rebalancing orders (live or dry run based on payload)

## Security

- Uses random client IDs to avoid IBKR login conflicts
- Supports both paper and live trading modes
- API keys configured via environment variables
- Non-root user in Docker container

## Monitoring

- Comprehensive logging with configurable levels
- Error handling with retry logic
- Connection health monitoring
- Trade execution logging

## Development

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python -m app.main
```

3. Run tests:
```bash
python -m app.cli dry-run
```

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check IBKR gateway is running and accessible
2. **Authentication Error**: Verify IBKR credentials in .env file
3. **API Errors**: Check allocation API URL and authentication
4. **Ably Connection**: Verify Ably API key and endpoint format

### Logs

Check application logs for detailed error information:
```bash
docker-compose logs portfolio-rebalancer
```

## License

MIT License - see LICENSE file for details.