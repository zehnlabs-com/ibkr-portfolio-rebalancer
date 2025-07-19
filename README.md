# IBKR Portfolio Rebalancer

A portfolio rebalancing service that automatically rebalances your Interative Brokers (IBKR) accounts based on allocations provided by Zehnlabs Tactical Asset Allocation strategies.

⚠️ **IMPORTANT DISCLAIMER**
This software is provided "as-is" without any warranty. Automated trading involves substantial risk of loss. You are solely responsible for your trading decisions and any resulting gains or losses. This is not financial advice. Always test thoroughly and consider consulting a financial advisor before using automated trading systems.

## Features

- **Event-Driven Rebalancing**: Subscribes to real-time endpoints for rebalancing triggers
- **Multi-Account Support**: Allows multiple IBKR accounts with different strategies
- **Robust Error Handling**: Indefinite event retention with automatic retry and queue management
- **Management Service**: RESTful API for queue monitoring and manual intervention
- **Docker Support**: Containerized deployment with existing IBKR gateway

## Architecture

The application follows a modular architecture with single responsibility principle:

```
event-broker/              # Event ingestion and queuing
event-processor/           # Event processing and execution
management-service/        # Queue monitoring and management
```

## Error Handling Strategy

The system implements a robust error handling strategy designed for reliability and visibility:

### Core Principles

1. **No Event Loss**: Events are retained indefinitely and automatically retried until successful
2. **Command-Level Deduplication**: Only one event per account+command combination can be active
3. **Fast Failure**: IBKR connection retries fail quickly to keep the queue moving
4. **Full Visibility**: Management service provides health monitoring, queue visibility, and control
5. **FIFO Retry**: Failed events go to the back of the queue for fair processing

### Event Lifecycle

1. **Event Ingestion**: Event broker receives rebalance events and queues them in Redis
2. **Deduplication**: Events are deduplicated by `account_id:command` (e.g., `DU123456:rebalance`)
3. **Processing**: Event processor dequeues events and executes appropriate commands
4. **Failure Handling**: Failed events are automatically requeued with incremented retry count
5. **Success Cleanup**: Successful events are removed from the active events set

### Queue Management

- **Redis Queue**: `rebalance_queue` stores pending events ready for processing
- **Delayed Queue**: `rebalance_delayed_set` stores failed events waiting for retry
- **Active Events**: `active_events` set tracks `account_id:command` combinations in progress
- **Times Queued**: Each event tracks how many times it has been queued for processing

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
4. **Calculate Target Positions**: Uses full account value for allocation calculations.
5. **Generate Orders**: Creates buy/sell orders to reach target allocation
6. **Execute Sell Orders**: Submits sell orders first and waits for completion (with timeout)
7. **Get Cash Balance**: Retrieves actual cash balance after sells complete
8. **Execute Buy Orders**: Submits buy orders up to `Cash Balance - (Account Value × Reserve %)`

**Order Cancellation:**
Before placing new rebalancing orders, the system automatically cancels all existing pending orders for the account to prevent duplicate or conflicting trades. 

**Important**: If existing orders cannot be cancelled within 60 seconds, the rebalancing process will fail with an error. This prevents the system from placing new orders when old orders are still pending, which could result in overtrading or unintended positions.

**Behavior:**
1. **Sell Orders Placed**: System places all sell orders and collects their order IDs
2. **Status Polling**: Polls order status every 2 seconds for up to 60 seconds (configurable)
3. **Success Case**: All sell orders complete → Buy orders execute with updated cash balance
4. **Timeout Case**: After 60 seconds → Event fails → Automatic retry mechanism triggers
5. **Retry Handling**: Next attempt starts fresh with current positions/cash state

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

**Reserve Calculation:**
The cash reserve is calculated based on **total account value**, not available cash:

**Example:**
- Account Value: $100,000
- Reserve: 2% of account value = $2,000
- Available Cash After Sells: $85,000
- Cash Available for Buy order: $85,000 - $2,000 = $83,000


## Event Flow

1. Zehnlabs publishes rebalance event to configured channel
2. Event broker receives event for specific account
3. Event is queued in Redis with deduplication (account+command level)
4. Event processor dequeues event 
5. Calls allocation API to get target percentages
6. Calculates required trades
7. Executes rebalancing orders
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
   curl -X DELETE http://localhost:8000/queue/events/{event-id-here}
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

## License

MIT License - see LICENSE file for details.