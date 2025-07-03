# Queue Migration Plan

## Overview

This document outlines the migration from the current HTTP-based architecture to a Redis queue-based architecture for improved reliability and simplified operation.

## Current vs Target Architecture

### Current Architecture
```
Event-Broker (Ably) → HTTP → Rebalancer-API (FastAPI) → IBKR Gateway
```

### Target Architecture
```
Event-Broker (Ably) → Redis Queue → Event-Processor (Simple Worker) → IBKR Gateway
                                  ↓
                               PostgreSQL (Event Tracking)
```

## Migration Strategy

### Phase 1: Create New Event-Processor Project
**Goal**: Create standalone event processing service reusing core business logic

#### 1.1 Project Structure
```
event-processor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Main worker loop
│   ├── config.py               # Configuration management
│   ├── logger.py               # Structured logging with event_id
│   ├── database.py             # PostgreSQL connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── events.py           # Event tracking models
│   │   ├── queue.py            # Queue message models
│   │   └── responses.py        # Rebalancing response models (adapted)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ibkr_client.py      # IBKR integration (reused 95%)
│   │   ├── allocation_service.py # External API client (reused 100%)
│   │   ├── rebalancer_service.py # Core rebalancing logic (reused 90%)
│   │   ├── event_service.py    # Event tracking service (new)
│   │   ├── queue_service.py    # Redis queue operations (new)
│   │   └── market_hours.py     # Market hours detection (new)
│   └── utils/
│       ├── __init__.py
│       └── retry.py            # Retry utilities (reused 100%)
├── config.yaml                 # Configuration file
├── requirements.txt            # Dependencies
├── Dockerfile                  # Container definition
└── tests/                      # Test suite
```

#### 1.2 Code Reuse Plan

**Direct Copy (95% reuse)**:
- `services/ibkr_client.py` (445 lines) → Remove FastAPI deps, add event_id logging
- `services/allocation_service.py` (89 lines) → No changes needed
- `services/rebalancer_service.py` (233 lines) → Remove HTTP response formatting
- `utils/retry.py` (83 lines) → No changes needed

**Adaptation (70-80% reuse)**:
- `models/responses.py` → Adapt for queue-based communication
- `config.py` → Remove FastAPI config, add Redis/PostgreSQL config
- `logger.py` → Add structured logging with event_id support

**New Components**:
- `services/event_service.py` → PostgreSQL event tracking
- `services/queue_service.py` → Redis queue operations
- `services/market_hours.py` → Market hours detection via IBKR API
- `models/events.py` → Event tracking data models
- `models/queue.py` → Queue message formats
- `database.py` → PostgreSQL connection management

### Phase 2: Modify Event-Broker
**Goal**: Replace HTTP client with Redis queue operations

#### 2.1 Event-Broker Changes

**Replace**:
- `services/rebalancer_client.py` (212 lines) → Remove completely
- `services/ably_service.py` → Modify to use Redis instead of HTTP

**Add**:
- Redis client integration
- Event deduplication logic using Redis sets
- Event tracking (PostgreSQL insert)
- GUID generation for events

#### 2.2 New Event-Broker Flow
```python
# Simplified event-broker flow
def handle_ably_event(event_data):
    event_id = str(uuid.uuid4())
    account_id = extract_account_id(event_data)
    
    # Track event in PostgreSQL
    db.insert_event(event_id, account_id, 'pending', event_data)
    
    # Check if account already queued
    if not redis.sismember("queued_accounts", account_id):
        # Add to queue and tracking set
        redis.sadd("queued_accounts", account_id)
        redis.lpush("rebalance_queue", {
            'event_id': event_id,
            'account_id': account_id,
            'data': event_data
        })
        logger.info("Event queued", event_id=event_id, account_id=account_id)
    else:
        logger.info("Account already queued", event_id=event_id, account_id=account_id)
```

### Phase 3: Database Schema
**Goal**: Implement event tracking and audit capabilities

#### 3.1 PostgreSQL Schema
```sql
-- Event tracking table
CREATE TABLE rebalance_events (
    event_id UUID PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    payload JSONB NOT NULL,
    error_message TEXT,
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    first_failed_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_events_account_id ON rebalance_events(account_id);
CREATE INDEX idx_events_status ON rebalance_events(status);
CREATE INDEX idx_events_received_at ON rebalance_events(received_at);
CREATE INDEX idx_events_created_at ON rebalance_events(created_at);

-- Retention policy (run daily)
-- DELETE FROM rebalance_events WHERE created_at < NOW() - INTERVAL '365 days';
```

#### 3.2 Event Service Implementation
```python
class EventService:
    def create_event(self, event_id: str, account_id: str, payload: dict) -> None:
        """Create new event record"""
        
    def update_status(self, event_id: str, status: str, error: str = None) -> None:
        """Update event status with optional error"""
        
    def increment_retry(self, event_id: str) -> int:
        """Increment retry count, return current count"""
        
    def should_retry(self, event_id: str, max_retry_days: int) -> bool:
        """Check if event should be retried based on day limit"""
```

### Phase 4: Configuration Changes
**Goal**: Update configuration for Redis and PostgreSQL

#### 4.1 Event-Processor Configuration
```yaml
# event-processor/config.yaml
redis:
  host: redis
  port: 6379
  db: 0
  max_connections: 10

postgresql:
  host: postgres
  port: 5432
  database: portfolio_rebalancer
  username: postgres
  password: postgres

ibkr:
  host: ibkr
  port: 7497
  connection_retry:
    max_retries: 3
    base_delay: 5
    max_delay: 60
    backoff_multiplier: 2.0
    jitter: true

processing:
  max_retry_days: 7
  market_hours_buffer: 60  # minutes before market close for MOC orders
  queue_timeout: 30        # seconds for redis.brpop

allocation:
  api_url: "https://api.zehnlabs.com/v1/allocation"
  timeout: 30

logging:
  level: INFO
  format: json
  retention_days: 365
```

#### 4.2 Event-Broker Configuration Updates
```yaml
# event-broker/config.yaml
ably:
  api_key: ${ABLY_API_KEY}
  channels:
    - "rebalance-events"

redis:
  host: redis
  port: 6379
  db: 0

postgresql:
  host: postgres
  port: 5432
  database: portfolio_rebalancer
  username: postgres
  password: postgres

logging:
  level: INFO
  format: json
  retention_days: 365
```

### Phase 5: Docker Compose Changes
**Goal**: Replace rebalancer-api with event-processor and add required services

#### 5.1 New Docker Compose Structure
```yaml
# docker-compose.yml
version: '3.8'

services:
  # Remove: rebalancer-api service
  
  # Add: Redis service
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Add: PostgreSQL service
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: portfolio_rebalancer
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Add: Event-Processor service
  event-processor:
    build: ./event-processor
    depends_on:
      - redis
      - postgres
      - ibkr
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
      - IBKR_HOST=ibkr
    volumes:
      - ./event-processor/logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "365"

  # Modify: Event-Broker service
  event-broker:
    build: ./event-broker
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
    volumes:
      - ./event-broker/logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "365"

  # Keep: IBKR Gateway (unchanged)
  ibkr:
    image: ghcr.io/gnzsnz/ib-gateway:latest
    environment:
      TWS_USERID: ${TWS_USERID}
      TWS_PASSWORD: ${TWS_PASSWORD}
      TRADING_MODE: ${TRADING_MODE:-paper}
      READ_ONLY_API: ${READ_ONLY_API:-no}
    ports:
      - "7497:7497"
    healthcheck:
      test: ["CMD", "netstat", "-tuln", "|", "grep", "7497"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  postgres_data:
```

### Phase 6: Implementation Details

#### 6.1 Main Worker Loop (event-processor/app/main.py)
```python
import asyncio
import json
import uuid
from datetime import datetime, time
from typing import Dict, Any

from app.config import config
from app.logger import logger
from app.services.queue_service import QueueService
from app.services.event_service import EventService
from app.services.rebalancer_service import RebalancerService
from app.services.market_hours import MarketHoursService
from app.services.ibkr_client import IBKRClient

class EventProcessor:
    def __init__(self):
        self.queue_service = QueueService()
        self.event_service = EventService()
        self.rebalancer_service = RebalancerService()
        self.market_hours_service = MarketHoursService()
        self.ibkr_client = IBKRClient()
        
    async def start(self):
        """Main event processing loop"""
        logger.info("Starting event processor")
        
        # Connect to IBKR
        if not await self.ibkr_client.connect():
            logger.error("Failed to connect to IBKR")
            return
            
        while True:
            try:
                # Check if markets are open
                if not await self.market_hours_service.is_market_open():
                    logger.info("Markets closed, waiting...")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Get next event from queue
                event_data = await self.queue_service.get_next_event()
                
                if event_data:
                    await self.process_event(event_data)
                    
            except Exception as e:
                logger.error("Error in main loop", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def process_event(self, event_data: Dict[str, Any]):
        """Process a single event"""
        event_id = event_data['event_id']
        account_id = event_data['account_id']
        
        try:
            # Update event status to processing
            await self.event_service.update_status(event_id, 'processing')
            
            # Remove from queued accounts set
            await self.queue_service.remove_from_queued(account_id)
            
            # Determine order type based on time
            order_type = await self.determine_order_type()
            
            # Execute rebalancing
            result = await self.rebalancer_service.rebalance_account(
                account_id, 
                event_data['data'],
                order_type
            )
            
            # Update event status to completed
            await self.event_service.update_status(event_id, 'completed')
            
            logger.info(
                "Event processed successfully",
                event_id=event_id,
                account_id=account_id,
                orders_placed=len(result.orders)
            )
            
        except Exception as e:
            logger.error(
                "Event processing failed",
                event_id=event_id,
                account_id=account_id,
                error=str(e)
            )
            
            # Handle retry logic
            await self.handle_failed_event(event_id, account_id, event_data, str(e))
    
    async def handle_failed_event(self, event_id: str, account_id: str, 
                                 event_data: Dict[str, Any], error: str):
        """Handle failed event with retry logic"""
        # Update event status to failed
        await self.event_service.update_status(event_id, 'failed', error)
        
        # Check if should retry
        if await self.event_service.should_retry(event_id, config.processing.max_retry_days):
            # Put back in queue for retry
            await self.queue_service.requeue_event(event_data)
            logger.info(
                "Event requeued for retry",
                event_id=event_id,
                account_id=account_id
            )
        else:
            logger.error(
                "Event exceeded retry limit",
                event_id=event_id,
                account_id=account_id
            )
    
    async def determine_order_type(self) -> str:
        """Determine order type based on market hours"""
        market_close_time = await self.market_hours_service.get_market_close_time()
        current_time = datetime.now().time()
        
        # Calculate time until market close
        time_until_close = datetime.combine(datetime.today(), market_close_time) - \
                          datetime.combine(datetime.today(), current_time)
        
        # Use MOC orders if within buffer period of market close
        if time_until_close.total_seconds() <= config.processing.market_hours_buffer * 60:
            return "MOC"
        else:
            return "MKT"

if __name__ == "__main__":
    processor = EventProcessor()
    asyncio.run(processor.start())
```

#### 6.2 Queue Service Implementation
```python
class QueueService:
    def __init__(self):
        self.redis = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            decode_responses=True
        )
    
    async def get_next_event(self) -> Dict[str, Any]:
        """Get next event from queue with timeout"""
        result = self.redis.brpop(
            "rebalance_queue", 
            timeout=config.processing.queue_timeout
        )
        
        if result:
            queue_name, event_json = result
            return json.loads(event_json)
        
        return None
    
    async def requeue_event(self, event_data: Dict[str, Any]):
        """Put event back in queue for retry"""
        # Add to front of queue
        self.redis.lpush("rebalance_queue", json.dumps(event_data))
        
        # Add account back to queued set
        account_id = event_data['account_id']
        self.redis.sadd("queued_accounts", account_id)
    
    async def remove_from_queued(self, account_id: str):
        """Remove account from queued set"""
        self.redis.srem("queued_accounts", account_id)
```

### Phase 7: Testing Strategy

#### 7.1 Unit Tests
- Test event processing logic
- Test queue operations
- Test retry mechanisms
- Test market hours detection

#### 7.2 Integration Tests
- Test Redis queue operations
- Test PostgreSQL event tracking
- Test IBKR integration
- Test end-to-end event flow

#### 7.3 Performance Tests
- Test queue throughput
- Test concurrent event processing
- Test memory usage
- Test error recovery

### Phase 8: Deployment Plan

#### 8.1 Migration Steps
1. **Backup current system**
2. **Deploy Redis and PostgreSQL services**
3. **Deploy event-processor service**
4. **Update event-broker with Redis integration**
5. **Remove rebalancer-api service**
6. **Update monitoring and logging**

#### 8.2 Rollback Plan
- Keep rebalancer-api code in separate branch
- Use feature flags for gradual migration
- Monitor queue metrics and event completion rates

### Phase 9: Monitoring and Maintenance

#### 9.1 Key Metrics
- Queue depth and processing rate
- Event success/failure rates
- IBKR connection health
- Database performance
- Log retention and rotation

#### 9.2 Log Search Commands
```bash
# Search by event ID
grep "event_id.*abc-123" /var/log/event-processor/*.log

# Search by account ID
grep "account_id.*DU123" /var/log/event-processor/*.log

# Search failed events
grep "failed" /var/log/event-processor/*.log | grep "event_id"
```

#### 9.3 Maintenance Tasks
- Daily: Clean up old events (365 days)
- Weekly: Monitor queue depths
- Monthly: Review error patterns
- Quarterly: Performance optimization

## Expected Benefits

1. **Simplified Architecture**: Remove FastAPI, async complexity, HTTP timeouts
2. **Improved Reliability**: Queue-based processing with automatic retries
3. **Better Monitoring**: Event tracking with detailed logs
4. **Easier Maintenance**: Single-threaded worker, simpler debugging
5. **Cost Reduction**: Eliminate robust pricing logic, reduce complexity
6. **Business Alignment**: Day-based retry strategy aligns with user behavior

## Risks and Mitigations

1. **Risk**: Redis single point of failure
   - **Mitigation**: Redis persistence, backup strategies

2. **Risk**: PostgreSQL performance with high event volume
   - **Mitigation**: Proper indexing, automated cleanup

3. **Risk**: IBKR connection issues
   - **Mitigation**: Reuse existing robust connection management

4. **Risk**: Event loss during transition
   - **Mitigation**: Parallel running during migration, comprehensive testing

## Timeline Estimate

- **Phase 1-2**: Event-processor creation and event-broker modification: 2 weeks
- **Phase 3-4**: Database schema and configuration: 1 week
- **Phase 5-6**: Docker setup and implementation: 1 week
- **Phase 7**: Testing and validation: 1 week
- **Phase 8**: Deployment and migration: 1 week
- **Phase 9**: Monitoring setup: 1 week

**Total**: 7 weeks for complete migration