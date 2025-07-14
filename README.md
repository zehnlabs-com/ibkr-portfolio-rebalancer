# IBKR Portfolio Rebalancer

An automated portfolio rebalancing service that integrates with Interactive Brokers and Ably.com for event-driven rebalancing.

## Features

- **Event-Driven Rebalancing**: Subscribes to Ably.com endpoints for real-time rebalancing triggers
- **Multi-Account Support**: Manage multiple IBKR accounts with different allocation strategies
- **Configurable Allocation APIs**: Fetch target allocations from external APIs
- **Dry-Run Mode**: Test rebalancing without executing actual trades
- **Robust Error Handling**: Indefinite event retention with automatic retry and queue management
- **Management Service**: RESTful API for queue monitoring and manual intervention
- **Command-Level Deduplication**: Multiple command types per account with smart deduplication
- **Modern IBKR Integration**: Uses ib_async (successor to ib_insync) for Interactive Brokers API
- **Docker Support**: Containerized deployment with existing IBKR gateway
- **Cash Reserve Management**: Configurable cash reserve applied after sells to improve order fill rates and handle price movements

## Architecture

The application follows a modular architecture with single responsibility principle:

```
event-broker/              # Event ingestion and queuing
├── app/
│   ├── services/
│   │   ├── ably_service.py    # Ably.com event subscription
│   │   ├── queue_service.py   # Redis queue management
│   │   └── event_service.py   # Database event tracking
│   └── main.py

event-processor/           # Event processing and execution
├── app/
│   ├── commands/          # Command pattern implementations
│   │   ├── rebalance.py   # Rebalancing logic
│   │   ├── print_*.py     # Information commands
│   │   └── cancel_orders.py
│   ├── services/
│   │   ├── ibkr_client.py     # IBKR connection and trading
│   │   ├── queue_service.py   # Redis queue consumption
│   │   └── allocation_service.py  # API calls for allocations
│   └── core/
│       └── event_processor.py  # Main processing loop

management-service/        # Queue monitoring and management
├── app/
│   ├── main.py           # FastAPI application
│   ├── queue_manager.py  # Queue inspection and manipulation
│   └── health.py         # Health check logic
```

## Error Handling Strategy

The system implements a robust error handling strategy designed for reliability and visibility:

### Core Principles

1. **No Event Loss**: Events are retained indefinitely and automatically retried until successful
2. **Command-Level Deduplication**: Only one event per account+command combination can be active
3. **Fast Failure**: IBKR connection retries fail quickly to keep the queue moving
4. **Full Visibility**: Management service provides complete queue visibility and control
5. **FIFO Retry**: Failed events go to the back of the queue for fair processing

### Event Lifecycle

1. **Event Ingestion**: Event broker receives events from Ably and queues them in Redis
2. **Deduplication**: Events are deduplicated by `account_id:command` (e.g., `DU123456:rebalance`)
3. **Processing**: Event processor dequeues events and executes appropriate commands
4. **Failure Handling**: Failed events are automatically requeued with incremented retry count
5. **Success Cleanup**: Successful events are removed from the active events set

### Queue Management

- **Redis Queue**: `rebalance_queue` stores pending events ready for processing
- **Delayed Queue**: `rebalance_delayed_set` stores failed events waiting for retry
- **Active Events**: `active_events` set tracks `account_id:command` combinations in progress
- **Times Queued**: Each event tracks how many times it has been queued for processing
- **Database Tracking**: PostgreSQL stores event history, status, and retry information

### Retry Behavior

- **Automatic Requeue**: Failed events are automatically moved to the delayed queue
- **Delayed Retry**: Failed events wait in delayed queue before being retried
- **Infinite Retries**: No limits on retry attempts - events retry until successful
- **Fixed Delays**: IBKR connection retries use fixed delays instead of exponential backoff
- **Queue Ordering**: Failed events don't block processing of other events

## Management Service

The management service provides a RESTful API for monitoring and controlling the event queue:

### API Endpoints

**Health Monitoring (Public)**
- `GET /health` - System health check (healthy if no events with retries or delayed events)
- `GET /queue/status` - Queue statistics and metrics including delayed events
- `GET /queue/events?limit=100` - List all events (active and delayed)
- `GET /queue/events?limit=100&type=active` - List only active events
- `GET /queue/events?limit=100&type=delayed` - List only delayed events

**Queue Management (Internal-Only)**
- `DELETE /queue/events/{event_id}` - Remove specific event from queue (searches both active and delayed)
- `POST /queue/events` - Add event to queue manually

### Internal Access

Queue management endpoints are internal-only and do not require authentication:

```bash
# Use with curl (no authentication needed)
curl -X DELETE http://localhost:8000/queue/events/some-event-id
```

### Health Check Integration

The health endpoint returns:
- **Healthy**: No events with `times_queued > 1` and no delayed events
- **Unhealthy**: One or more events are being retried or are in delayed queue
- **Error**: Service cannot check queue status

Example health response:
```json
{
  "status": "healthy",
  "healthy": true,
  "events_with_retries": 0,
  "delayed_events": 0,
  "message": "No events require retry"
}
```

### Queue Status Response

```json
{
  "queue_length": 5,
  "active_events_count": 3,
  "delayed_events_count": 2,
  "oldest_event_age_seconds": 120,
  "events_with_retries": 1
}
```

### Event Details Response

```json
[
  {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "account_id": "DU123456",
    "exec_command": "rebalance",
    "times_queued": 3,
    "created_at": "2023-12-01T10:00:00Z",
    "type": "active",
    "data": {
      "exec": "rebalance",
      "account_config": {...}
    }
  },
  {
    "event_id": "550e8400-e29b-41d4-a716-446655440001",
    "account_id": "DU789012",
    "exec_command": "rebalance",
    "times_queued": 5,
    "created_at": "2023-12-01T09:30:00Z",
    "type": "delayed",
    "retry_after": "2023-12-01T10:45:00Z",
    "data": {
      "exec": "rebalance",
      "account_config": {...}
    }
  }
]
```

### Manual Event Management

Add an event manually:
```bash
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "rebalance",
    "data": {"exec": "rebalance"}
  }' \
  http://localhost:8000/queue/events
```

Remove a problematic event:
```bash
curl -X DELETE http://localhost:8000/queue/events/event-id-here
```

## Configuration

### Accounts Configuration

Edit `accounts.yaml` to configure your IBKR accounts:

```yaml
- account_id: "DU123456"
  notification:
    channel: "strategy-name-100"
  rebalancing:
    cash_reserve_percentage: 1.0  # 1% cash reserve (default)

- account_id: "DU789012"
  notification:
    channel: "strategy-name-200"
  rebalancing:
    cash_reserve_percentage: 2.5  # 2.5% cash reserve
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
IB_USERNAME=your_username
IB_PASSWORD=your_password
TRADING_MODE=paper

# Global API Keys (shared across all accounts)
ALLOCATIONS_API_KEY=your_allocation_key

# Management Service
# MANAGEMENT_API_KEY=no_longer_needed

# Order Configuration
# Note: Only MKT orders are supported (MOC not compatible with sell-first logic)
TIME_IN_FORCE=GTC
EXTENDED_HOURS_ENABLED=true

# VNC Configuration
VNC_PASSWORD=password

# Application Settings
LOG_LEVEL=INFO
```

**Important Environment Variables:**
- `TRADING_MODE`: Set to `paper` for testing or `live` for production
- `LOG_LEVEL`: Controls logging verbosity (DEBUG, INFO, WARNING, ERROR)

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
{"exec": "rebalance"}
```

**Dry Run (default for safety):**
```json
{}
```
or 
```json
{"exec": "dry_run"}
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
# All services
docker-compose logs -f

# Specific services
docker-compose logs -f event-broker
docker-compose logs -f event-processor
docker-compose logs -f management-service
```

3. Verify system health:
```bash
# Check management service health
curl http://localhost:8000/health

# Check queue status
curl http://localhost:8000/queue/status
```

### Manual Event Testing

Test rebalancing by manually adding events via the management service:

```bash
# Add a dry run event
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "print-rebalance",
    "data": {"exec": "print-rebalance"}
  }' \
  http://localhost:8000/queue/events

# Add a live rebalance event
curl -H "Content-Type: application/json" \
  -d '{
    "account_id": "DU123456",
    "exec_command": "rebalance",
    "data": {"exec": "rebalance"}
  }' \
  http://localhost:8000/queue/events
```

## Rebalancing Algorithm

The rebalancer implements a sell-first portfolio rebalancing algorithm with cash reserve management:

1. **Fetch Target Allocations**: Calls configured API to get target percentages
2. **Get Current Positions**: Retrieves current holdings from IBKR
3. **Cancel Existing Orders**: Cancels all pending orders to prevent conflicts (waits up to 60 seconds for confirmation)
4. **Calculate Target Positions**: Uses full account value for allocation calculations
5. **Generate Orders**: Creates buy/sell orders to reach target allocation
6. **Execute Sell Orders**: Submits sell orders first and waits for completion (with timeout)
7. **Get Cash Balance**: Retrieves actual cash balance after sells complete
8. **Execute Buy Orders**: Submits buy orders up to `Cash Balance - (Account Value × Reserve %)`

### Order Cancellation

Before placing new rebalancing orders, the system automatically cancels all existing pending orders for the account to prevent duplicate or conflicting trades. 

**Important**: If existing orders cannot be cancelled within 60 seconds, the rebalancing process will fail with an error. This prevents the system from placing new orders when old orders are still pending, which could result in overtrading or unintended positions.

### Order Completion Timeout

The system implements order completion timeout to prevent insufficient funds errors when placing buy orders:

**Problem Solved:**
- Previously, sell orders were placed and buy orders were immediately executed using estimated cash balance
- This caused "insufficient funds" errors when sell orders hadn't completed yet
- Buy orders would be rejected because the actual cash from sells wasn't available

**Solution:**
After placing sell orders, the system polls their status every 2 seconds until they complete or timeout occurs.

**Configuration:**
Order completion timeout is configurable in `event-processor/config/config.yaml`:

```yaml
ibkr:
  # Order completion timeout - how long to wait for sell orders to complete
  order_completion_timeout: 60  # Seconds (default: 60)
```

**Behavior:**
1. **Sell Orders Placed**: System places all sell orders and collects their order IDs
2. **Status Polling**: Polls order status every 2 seconds for up to 60 seconds (configurable)
3. **Success Case**: All sell orders complete → Buy orders execute with updated cash balance
4. **Timeout Case**: After 60 seconds → Event fails → Automatic retry mechanism triggers
5. **Retry Handling**: Next attempt starts fresh with current positions/cash state

**Benefits:**
- **Eliminates insufficient funds errors**: Buy orders only execute after sell proceeds are available
- **Handles partial fills gracefully**: Retry mechanism accounts for any orders that completed during timeout
- **Self-correcting**: Each retry evaluates fresh account state and only places needed orders
- **Configurable timeout**: Can be adjusted based on market conditions and order complexity

**Timeout Recovery:**
If sell orders don't complete within the timeout period:
1. The rebalancing event fails with a timeout error
2. The event is automatically requeued for retry (standard failure handling)
3. The next retry attempt starts with fresh account data
4. Only the remaining trades needed are calculated and executed
5. Process continues until successful completion

This approach leverages the existing robust retry infrastructure while ensuring order sequencing prevents trading errors.

### Cash Reserve System

The system maintains a configurable cash reserve applied after sell orders complete to improve order fill rates and handle market volatility:

**Purpose:**
- **Improved Fill Rates**: Market orders are more likely to fill when there's a cash buffer for price movements
- **Settlement Buffer**: Provides cushion for trade settlement and fees
- **Risk Management**: Prevents over-leveraging the account

**Configuration:**
Each account can have its own reserve percentage configured in `accounts.yaml`:

```yaml
- account_id: "DU123456"
  rebalancing:
    cash_reserve_percentage: 1.0  # 1% reserve (default)
```

**Validation:**
- **Range**: 0% to 10% (values outside this range default to 1%)
- **Default**: 1% if not specified or invalid
- **Logging**: Invalid values are logged with warnings

**Reserve Calculation:**
The cash reserve is calculated based on **total account value**, not available cash:

**Example:**
- Account Value: $100,000
- Reserve: 2% of account value = $2,000
- Available Cash After Sells: $5,000
- Cash Available for Purchases: $5,000 - $2,000 = $3,000

### API Response

The dry run and live rebalancing API responses now include detailed equity information:

```json
{
  "account_id": "DU123456",
  "execution_mode": "dry_run",
  "equity_info": {
    "total_equity": 100000.00,
    "cash_reserve_percentage": 1.0,
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
2. Event broker receives event for specific account
3. Event is queued in Redis with deduplication (account+command level)
4. Event processor dequeues event and parses payload to determine execution mode:
   - `{"exec": "rebalance"}` → Live execution
   - No payload or other values → Dry run (safe default)
5. Calls allocation API to get target percentages
6. Calculates required trades
7. Executes rebalancing orders (live or dry run based on payload)
8. On failure, event is automatically requeued for retry

## Security

- Uses random client IDs to avoid IBKR login conflicts
- Supports both paper and live trading modes
- Internal management API without authentication
- Non-root user in Docker container

## Monitoring

- Comprehensive logging with configurable levels
- Error handling with retry logic
- Connection health monitoring
- Trade execution logging

## Development

### Local Development

1. Install dependencies for each service:
```bash
# Event Broker
cd event-broker && pip install -r requirements.txt

# Event Processor
cd event-processor && pip install -r requirements.txt

# Management Service
cd management-service && pip install -r requirements.txt
```

2. Run the services (in separate terminals):
```bash
# Event Broker
cd event-broker && python -m app.main

# Event Processor  
cd event-processor && python main.py

# Management Service
cd management-service && python -m app.main
```

3. Test the system:
```bash
# Check system health
curl http://localhost:8000/health

# Add a test event
curl -H "Content-Type: application/json" \
  -d '{"account_id": "DU123456", "exec_command": "print-rebalance", "data": {"exec": "print-rebalance"}}' \
  http://localhost:8000/queue/events
```

## Troubleshooting

### Common Issues

#### Connection Problems
1. **IBKR Connection Failed**: 
   - Check IBKR gateway is running and accessible
   - Verify IBKR credentials in .env file
   - Ensure correct port (4004 for gateway, 7497 for TWS paper)
   - Check if client ID conflicts exist

2. **Redis Connection Failed**:
   - Verify Redis service is running: `docker-compose ps redis`
   - Check Redis logs: `docker-compose logs redis`
   - Ensure Redis port 6379 is accessible

3. **Database Connection Failed**:
   - Verify PostgreSQL service is running: `docker-compose ps postgres`
   - Check database logs: `docker-compose logs postgres`
   - Ensure database schema is initialized

#### Event Processing Issues
1. **Events Not Processing**:
   - Check event-processor logs: `docker-compose logs event-processor`
   - Verify queue has events: `curl http://localhost:8000/queue/status`
   - Check if event-processor is running: `docker-compose ps event-processor`

2. **Events Stuck in Queue**:
   - Check health status: `curl http://localhost:8000/health`
   - View problematic events: `curl http://localhost:8000/queue/events`
   - Check delayed events: `curl http://localhost:8000/queue/events?type=delayed`
   - Check for IBKR connection issues in logs

3. **Duplicate Events**:
   - System prevents duplicates via account+command deduplication
   - Check active events: `curl http://localhost:8000/queue/status`
   - Multiple command types per account are allowed (e.g., rebalance + print-positions)

#### Management Service Issues
1. **Management Service Not Accessible**:
   - Check service is running: `docker-compose ps management-service`
   - Verify port 8000 is accessible
   - Check management service logs: `docker-compose logs management-service`

2. **Management API Access**:
   - Management API is internal-only and doesn't require authentication
   - Ensure services are running in the same Docker network

#### Queue Management
1. **Clear Stuck Events**:
   ```bash
   # Remove specific event
   curl -X DELETE http://localhost:8000/queue/events/event-id-here
   ```

2. **Monitor Queue Health**:
   ```bash
   # Check overall system health
   curl http://localhost:8000/health
   
   # Get detailed queue status
   curl http://localhost:8000/queue/status
   
   # List events with retry counts
   curl http://localhost:8000/queue/events?limit=50
   
   # List only delayed events
   curl http://localhost:8000/queue/events?type=delayed
   ```

3. **Add Event Manually**:
   ```bash
   curl -H "Content-Type: application/json" \
     -d '{"account_id": "DU123456", "exec_command": "rebalance", "data": {"exec": "rebalance"}}' \
     http://localhost:8000/queue/events
   ```

### Logs

Check application logs for detailed error information:

```bash
# All services
docker-compose logs -f

# Specific services
docker-compose logs -f event-broker
docker-compose logs -f event-processor
docker-compose logs -f management-service

# Recent logs with timestamps
docker-compose logs -f --tail=100 -t event-processor
```

### Health Monitoring

The management service provides health endpoints for monitoring:

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed queue status
curl http://localhost:8000/queue/status

# Integration with monitoring tools
curl -s http://localhost:8000/health | jq '.healthy'
```

### Performance Monitoring

Monitor queue performance and retry patterns:

```bash
# Watch queue length over time
watch -n 5 'curl -s http://localhost:8000/queue/status | jq ".queue_length"'

# Monitor events with retries
curl -s http://localhost:8000/queue/status | jq '.events_with_retries'

# Check oldest event age
curl -s http://localhost:8000/queue/status | jq '.oldest_event_age_seconds'
```

### Recovery Procedures

1. **System Recovery After Failure**:
   - Events automatically retry - no manual intervention needed
   - Check management service for stuck events
   - Failed events will continue retrying until successful

2. **Database Recovery**:
   - Event history is preserved in PostgreSQL
   - Queue state is rebuilt from Redis on restart
   - Use `init.sql` to recreate database schema if needed

3. **Queue Recovery**:
   - Events in Redis queue will be processed when event-processor restarts
   - Active events set is rebuilt during processing
   - No events are lost during service restarts

## License

MIT License - see LICENSE file for details.