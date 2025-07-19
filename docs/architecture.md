# Architecture

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