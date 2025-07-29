# Event Processor Service

## Purpose

The Event Processor is the core execution engine that processes queued rebalancing events and executes trades through the Interactive Brokers gateway. It handles complex trading logic, retry mechanisms, and error recovery.

## Key Responsibilities

- **Event Processing**: Dequeues events from Redis and processes them sequentially
- **Trade Execution**: Executes buy/sell orders through IBKR Gateway
- **Trading Hours Validation**: Validates market hours before executing trades
- **Delayed Execution**: Schedules events for execution during market hours
- **Error Recovery**: Implements sophisticated retry logic with automatic requeuing
- **Portfolio Management**: Calculates trades based on target allocations
- **User Notifications**: Sends real-time notifications about event processing via [ntfy.sh](../user-notifications.md)

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


## IBKR Integration

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

### Trading Hours Validation
- **Contract Details**: Fetches trading hours for each symbol via IBKR API
- **Hours Selection**: Uses `LiquidHours` by default, `TradingHours` when `EXTENDED_HOURS_ENABLED=true`
- **Pre-execution Check**: Validates all symbols before getting market prices
- **Timezone Handling**: All times processed in America/New_York timezone

## Error Handling & Retry Logic

### Retry Behavior
- **Connection Failures**: Fast failure and retry
- **Order Failures**: Automatic requeuing with delay
- **API Errors**: Event requeuing for later retry
- **Infinite Retries**: Events retry until successful or removed manually

### Queue Management
- Failed events move to retry queue
- **Trading Hours Events**: Events outside trading hours move to delayed execution queue
- **Delayed Processing**: Background processor checks every minute for ready delayed events
- FIFO processing maintains order fairness
- All events eventually process (unless manually removed)

## Integration Points

### Upstream
- **Redis Queue**: Dequeues events from `rebalance_queue`
- **Retry Queue**: Processes retry events from `rebalance_retry_set`
- **Delayed Queue**: Processes delayed events from `delayed_execution_set`

### Downstream  
- **IBKR Gateway**: Executes trades via Interactive Brokers API
- **Allocation API**: Fetches target portfolio allocations from Zehnlabs

## Troubleshooting

### Common Issues

**Service won't connect to IBKR:**
- Verify IBKR Gateway is running and logged in
- Check trading mode matches IBKR configuration

**API Errors:**
- Verify you have valid subscription to Zehnlabs strategies
- Ensure your API keys are correct

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

# Check retry events
curl http://localhost:8000/queue/events?type=retry

# Check delayed events
curl http://localhost:8000/queue/events?type=delayed
```

## Docker Configuration

The service runs with:
- Restart on failure policy
- Volume mounts for configuration and logs  
- Network access to IBKR Gateway and Redis
- Health checks and monitoring