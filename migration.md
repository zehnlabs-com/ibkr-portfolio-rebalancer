# Service Separation Migration Plan

## Current Architecture Analysis

The current system is a monolithic application with several components running within a single process:

### Current Components
- **Main Application** (`app/main.py`): Entry point that initializes and orchestrates all services
- **IBKR Client** (`app/services/ibkr_client.py`): Handles Interactive Brokers API connections and trading operations
- **Ably Service** (`app/services/ably_service.py`): Subscribes to Ably channels for real-time events
- **Rebalancer Service** (`app/services/rebalancer_service.py`): Core portfolio rebalancing logic
- **Allocation Service** (`app/services/allocation_service.py`): Fetches target allocations from external APIs

### Current Issues
1. **Event Loop Conflicts**: Single process manages both Ably subscriptions and IBKR connections, causing blocking issues
2. **Resource Sharing**: All services share the same event loop and memory space
3. **Scalability**: Cannot scale event subscription and rebalancing independently
4. **Error Isolation**: Issues in one component can affect the entire application
5. **Deployment Complexity**: All services must be deployed together

## Target Architecture

Split the monolithic service into two distinct, independently deployable services:

### Service A: Event Subscriber
**Responsibility**: Subscribe to Ably events and trigger rebalancing via HTTP calls
- Lightweight, event-driven service
- Manages multiple Ably channel subscriptions
- Makes HTTP calls to the Rebalancer Service
- Handles event filtering and payload validation

### Service B: Rebalancer Service
**Responsibility**: REST API service that performs portfolio rebalancing
- FastAPI-based HTTP service
- Manages IBKR connections and trading operations
- Handles allocation fetching and portfolio calculation
- Provides both live and dry-run endpoints

## Detailed Migration Plan

### Phase 1: Create Rebalancer API Service

#### 1.1 New Service Structure
```
rebalancer-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py      # Pydantic request models
│   │   └── responses.py     # Pydantic response models
│   └── services/
│       ├── __init__.py
│       ├── ibkr_client.py   # Moved from current service
│       ├── allocation_service.py  # Moved from current service
│       └── rebalancer_service.py  # Moved from current service
├── requirements.txt
├── Dockerfile
└── accounts.yaml
```

#### 1.2 FastAPI Endpoints
- `POST /rebalance/{account_id}` - Trigger rebalancing for specific account
- `POST /rebalance/{account_id}/dry-run` - Dry run rebalancing
- `GET /accounts` - List configured accounts
- `GET /health` - Health check endpoint
- `GET /accounts/{account_id}/positions` - Get current positions
- `GET /accounts/{account_id}/value` - Get account value

#### 1.3 Request/Response Models
```python
# Request Models
class RebalanceRequest(BaseModel):
    execution_mode: str = "dry_run"  # "rebalance" for live execution

# Response Models
class RebalanceResponse(BaseModel):
    account_id: str
    execution_mode: str
    orders: List[RebalanceOrder]
    status: str
    message: str
    timestamp: datetime

class RebalanceOrder(BaseModel):
    symbol: str
    quantity: int
    action: str  # BUY/SELL
    market_value: float
```

### Phase 2: Create Event Subscriber Service

#### 2.1 New Service Structure
```
event-subscriber/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   └── services/
│       ├── __init__.py
│       ├── ably_service.py  # Enhanced Ably service
│       └── rebalancer_client.py  # HTTP client for rebalancer API
├── requirements.txt
├── Dockerfile
└── accounts.yaml
```

#### 2.2 HTTP Client for Rebalancer Service
```python
class RebalancerClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
    
    async def trigger_rebalance(self, account_id: str, execution_mode: str):
        # Make HTTP POST to rebalancer service
        pass
    
    async def health_check(self):
        # Check if rebalancer service is healthy
        pass
```

### Phase 3: Configuration Changes

#### 3.1 Environment Variables
**Event Subscriber Service:**
```bash
# Service Configuration
REBALANCER_API_URL=http://rebalancer-api:8000
REBALANCER_API_TIMEOUT=60

# Ably Configuration
REALTIME_API_KEY=your_ably_api_key

# Application Settings
LOG_LEVEL=INFO
```

**Rebalancer API Service:**
```bash
# IBKR Configuration
IBKR_HOST=ibkr
IBKR_PORT=8888
IBKR_USERNAME=your_username
IBKR_PASSWORD=your_password
TRADING_MODE=paper

# API Configuration
ALLOCATIONS_API_KEY=your_allocation_key

# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Application Settings
LOG_LEVEL=INFO
```

#### 3.2 Docker Compose Changes
```yaml
services:
  ibkr:
    # ... existing IBKR configuration

  rebalancer-api:
    build:
      context: ./rebalancer-api
      dockerfile: Dockerfile
    container_name: rebalancer-api
    environment:
      - IBKR_HOST=ibkr
      - IBKR_PORT=${IBKR_PORT}
      - IBKR_USERNAME=${IBKR_USERNAME}
      - IBKR_PASSWORD=${IBKR_PASSWORD}
      - TRADING_MODE=${TRADING_MODE:-paper}
      - ALLOCATIONS_API_KEY=${ALLOCATIONS_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - ibkr
    ports:
      - "8000:8000"
    restart: unless-stopped

  event-subscriber:
    build:
      context: ./event-subscriber
      dockerfile: Dockerfile
    container_name: event-subscriber
    environment:
      - REBALANCER_API_URL=http://rebalancer-api:8000
      - REALTIME_API_KEY=${REALTIME_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - rebalancer-api
    restart: unless-stopped
```

### Phase 4: Data Flow Design

#### 4.1 Event Flow
1. **Ably Event Received** → Event Subscriber Service
2. **HTTP Request** → Event Subscriber → Rebalancer API
3. **Portfolio Analysis** → Rebalancer API → IBKR + Allocation APIs
4. **Order Execution** → Rebalancer API → IBKR
5. **Response** → Rebalancer API → Event Subscriber

#### 4.2 Error Handling
- **Network Failures**: Retry logic with exponential backoff
- **API Errors**: Proper error responses and logging
- **IBKR Connection Issues**: Health checks and reconnection logic
- **Service Unavailability**: Circuit breaker pattern

### Phase 5: Monitoring and Observability

#### 5.1 Health Checks
- **Event Subscriber**: Ably connection status, last event received timestamp
- **Rebalancer API**: IBKR connection status, API endpoint health
- **Inter-Service**: HTTP connectivity between services

#### 5.2 Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Log Aggregation**: Central logging for both services
- **Error Tracking**: Detailed error logs with stack traces

#### 5.3 Metrics
- **Event Subscriber**: Events received, HTTP requests made, success/failure rates
- **Rebalancer API**: API requests, rebalancing operations, order execution rates
- **System**: Resource usage, response times, error rates

### Phase 6: Security Considerations

#### 6.1 Inter-Service Communication
- **Internal Network**: Services communicate over internal Docker network
- **API Keys**: Separate API keys for each service
- **Request Validation**: Input validation and sanitization

#### 6.2 Secrets Management
- **Environment Variables**: Sensitive data in environment variables
- **Container Secrets**: Use Docker secrets for production
- **Credential Rotation**: Support for rotating API keys and passwords

### Phase 7: Testing Strategy

#### 7.1 Unit Tests
- **Service Logic**: Test individual service components
- **API Endpoints**: Test FastAPI endpoints with mock data
- **Error Handling**: Test error scenarios and recovery

#### 7.2 Integration Tests
- **Service Communication**: Test HTTP communication between services
- **End-to-End**: Test complete event flow from Ably to IBKR
- **Error Scenarios**: Test service failures and recovery

#### 7.3 Performance Tests
- **Load Testing**: Test API performance under load
- **Stress Testing**: Test service behavior under stress
- **Scalability**: Test horizontal scaling capabilities

### Phase 8: Deployment Strategy

#### 8.1 Blue-Green Deployment
- **Zero Downtime**: Deploy new version without interrupting service
- **Rollback Capability**: Quick rollback to previous version if issues
- **Health Checks**: Automated health checks before switching traffic

#### 8.2 Staged Rollout
1. **Development Environment**: Test in development first
2. **Staging Environment**: Full integration testing
3. **Production Deployment**: Gradual rollout to production

#### 8.3 Migration Steps
1. **Deploy Rebalancer API** alongside existing service
2. **Test API Endpoints** with existing service as client
3. **Deploy Event Subscriber** pointing to new API
4. **Verify End-to-End Flow** in parallel with existing service
5. **Switch Traffic** from old service to new services
6. **Decommission Old Service** after verification period

## Benefits of New Architecture

### 8.1 Scalability
- **Independent Scaling**: Scale event processing and rebalancing independently
- **Resource Optimization**: Allocate resources based on service needs
- **Horizontal Scaling**: Add more instances of either service as needed

### 8.2 Reliability
- **Fault Isolation**: Issues in one service don't affect the other
- **Service Recovery**: Services can recover independently
- **Circuit Breaker**: Prevent cascade failures

### 8.3 Maintainability
- **Separation of Concerns**: Each service has a single responsibility
- **Independent Development**: Teams can work on services independently
- **Technology Flexibility**: Use different technologies for different services

### 8.4 Performance
- **Event Loop Isolation**: No more event loop conflicts
- **Optimized Resources**: Each service optimized for its specific task
- **Reduced Blocking**: Non-blocking HTTP communication

## Migration Timeline

### Week 1-2: Development
- Create FastAPI rebalancer service
- Implement core endpoints and business logic
- Write unit tests

### Week 3: Integration
- Create event subscriber service
- Implement HTTP client communication
- Integration testing

### Week 4: Testing & Deployment
- Performance testing
- Security review
- Staging deployment and validation
- Production deployment

## Risk Mitigation

### Technical Risks
- **Network Latency**: Monitor and optimize HTTP communication
- **Service Dependencies**: Implement proper health checks and retries
- **Data Consistency**: Ensure consistent state across services

### Operational Risks
- **Deployment Complexity**: Use automated deployment pipelines
- **Monitoring Gaps**: Comprehensive monitoring and alerting
- **Troubleshooting**: Distributed tracing and centralized logging

## Conclusion

This migration will transform the monolithic rebalancer into a modern, scalable microservices architecture. The separation of concerns between event handling and portfolio rebalancing will resolve the current event loop issues while providing better scalability, maintainability, and reliability.

The phased approach ensures minimal disruption to the existing system while providing comprehensive testing and validation at each stage. The new architecture will be well-positioned for future enhancements and scaling requirements.