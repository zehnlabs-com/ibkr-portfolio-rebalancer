# Event Processor Service

## Purpose

The Event Processor is the core execution engine that processes queued rebalancing events and executes trades through the Interactive Brokers API. It handles complex trading logic, retry mechanisms, and error recovery.

## Key Responsibilities

- **Event Processing**: Dequeues events from Redis and processes them sequentially
- **Trade Execution**: Executes buy/sell orders through IBKR Gateway
- **Error Recovery**: Implements sophisticated retry logic with automatic requeuing
- **Portfolio Management**: Calculates optimal trades based on target allocations

## Command Types

The service supports several command types:

- **`rebalance`** - Execute portfolio rebalancing trades
- **`print_positions`** - Display current portfolio positions
- **`print_orders`** - Show pending and recent orders
- **`print_equity`** - Display account equity information
- **`cancel_orders`** - Cancel pending orders
- **`print_rebalance`** - Preview rebalancing trades without execution

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `IB_HOST` | IBKR Gateway hostname | No (defaults to `ibkr`) |
| `TRADING_MODE` | Trading mode (`paper` or `live`) | No (defaults to `paper`) |
| `LOG_LEVEL` | Logging level | No (defaults to INFO) |
| `ALLOCATIONS_API_KEY` | API key for strategy allocations | Yes |
| `EXTENDED_HOURS_ENABLED` | Enable extended hours trading | No (defaults to `false`) |
| `SERVICE_VERSION` | Service version for monitoring | Yes |

### Configuration File

The service uses `/event-processor/config.yaml` for detailed configuration:

```yaml
redis:
  host: redis              # Redis server hostname
  port: 6379              # Redis server port
  db: 0                   # Redis database number
  max_connections: 10     # Connection pool size

ibkr:
  host: "ibkr"            # IBKR Gateway hostname
  
  connection_retry:
    max_retries: 3        # Connection retry attempts
    delay: 5              # Delay between retries (seconds)
  
  order_retry:
    max_retries: 2        # Order retry attempts
    delay: 1              # Delay between order retries (seconds)
  
  order_completion_timeout: 60  # Order completion timeout (seconds)

processing:
  queue_timeout: 30           # Queue polling timeout
  startup_max_attempts: 500   # Startup retry attempts
  startup_delay: 10           # Startup retry delay
  startup_initial_delay: 30   # Initial startup delay
  retry_delay_seconds: 60     # Failed event retry delay
  retry_check_interval: 60    # Retry check frequency

allocation:
  api_url: "https://workers.fintech.zehnlabs.com/api/v1/strategies"
  timeout: 30                 # API request timeout

logging:
  level: INFO             # Log level
  format: json            # Log format
```

## IBKR Integration

### Trading Modes
- **Paper Trading**: Safe testing environment with simulated trades
- **Live Trading**: Real money trading (use with extreme caution)

### Connection Management
- Automatic connection retry with configurable attempts
- Random client ID generation to avoid conflicts
- Connection health monitoring

### Order Execution
- Only Market orders supported
- Fractional shares are NOT supported due to IBKR API limitations
- Order status tracking and completion verification
- Automatic retry for temporary failures
- Cash reserve management for improved fill rates

## Error Handling & Retry Logic

### Retry Behavior
- **Connection Failures**: Fast retry with limited attempts
- **Order Failures**: Automatic requeuing with delay
- **API Errors**: Event requeuing for later retry
- **Infinite Retries**: Events retry until successful or removed manually

### Queue Management
- Failed events move to delayed queue
- FIFO processing maintains order fairness
- No event loss - all events eventually process

## Integration Points

### Upstream
- **Redis Queue**: Dequeues events from `rebalance_queue`
- **Delayed Queue**: Processes retry events from `rebalance_delayed_set`

### Downstream  
- **IBKR Gateway**: Executes trades via Interactive Brokers API
- **Allocation API**: Fetches target portfolio allocations from Zehnlabs

## Health Monitoring

The service provides monitoring through:
- Comprehensive JSON logging
- Connection status reporting
- Trade execution tracking
- Error rate monitoring

## Troubleshooting

### Common Issues

**Service won't connect to IBKR:**
- Verify IBKR Gateway is running and logged in
- Check trading mode matches IBKR configuration

**Orders not executing:**
- Ensure your IBKR account has proper permissions
- Check market hours and extended hours settings
- Verify account has sufficient buying power
- Review order logs for rejection reasons

**Events stuck in processing:**
- Check IBKR connection status
- Review retry queue for backed up events

### Monitoring Commands

```bash
# Check service status
docker-compose ps event-processor

# View detailed logs
docker-compose logs -f event-processor

# Monitor queue processing
curl http://localhost:8000/queue/status

# Check delayed/retry events
curl http://localhost:8000/queue/events?type=delayed
```

## Docker Configuration

The service runs with:
- Restart on failure policy
- Volume mounts for configuration and logs  
- Network access to IBKR Gateway and Redis
- Health checks and monitoring