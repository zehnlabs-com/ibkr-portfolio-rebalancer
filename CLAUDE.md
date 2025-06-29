# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Start all services (IBKR Gateway + API)
docker-compose up -d

# Start API only for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# View API documentation
http://localhost:8000/docs

# Health check
curl http://localhost:8000/api/v1/health

# Test calculate endpoint
curl -X POST "http://localhost:8000/api/v1/calculate" \
  -H "Content-Type: application/json" \
  -d '{"allocations": [{"symbol": "QQQ", "allocation": 0.6}, {"symbol": "SPY", "allocation": 0.4}]}'

# Check IBKR connection status
curl http://localhost:8000/api/v1/connection/status

# Get account information
curl http://localhost:8000/api/v1/account/info
```

### Container Management
```bash
# View container status
docker-compose ps

# View logs
docker-compose logs -f rebalancer-api  # API logs
docker-compose logs -f ibkr            # IBKR Gateway logs

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build
```

### Testing API Endpoints
Use `test.rest` file with REST client or copy commands for curl testing.

## Architecture Overview

### Service Architecture
This is a **FastAPI-based portfolio rebalancing service** that connects to Interactive Brokers (IBKR) for automated trading:

- **API Layer**: FastAPI application (`app/main.py`) with portfolio management endpoints
- **IBKR Integration**: Uses `ib_async` library to connect to IBKR Gateway/TWS
- **Docker Deployment**: Two-container setup (IBKR Gateway + FastAPI API)
- **Synchronous Design**: Recently converted from async to sync for simplicity

### Core Components

**Configuration** (`app/config.py`):
- Uses `pydantic-settings` for environment-based configuration
- Key settings: IBKR host/port, account type (paper/live), connection parameters

**Models** (`app/models.py`):
- `AllocationRequest`: Target portfolio allocation per symbol
- `RebalanceRequest`: Collection of allocations with validation (must sum to 1.0)
- `CalculatedOrder`: Individual buy/sell order details
- Response models for API endpoints

**IBKR Client** (`app/services/ibkr_client.py`):
- Synchronous wrapper around `ib_async` library
- Handles connection management with retry logic and random client IDs
- Key methods: `get_account_value()`, `get_positions()`, `get_current_price()`, `place_order()`

**Portfolio Rebalancer** (`app/services/rebalancer.py`):
- Core business logic for portfolio rebalancing
- `calculate_orders()`: Determines buy/sell orders needed to reach target allocations
- `execute_rebalance()`: Executes the calculated orders
- Orders are sorted (sells first, then buys) to free up cash before purchasing

**API Routes** (`app/routers/portfolio.py`):
- `/api/v1/calculate`: Calculate required orders without executing (dry-run)
- `/api/v1/rebalance`: Execute portfolio rebalancing
- `/api/v1/account/info`: Get current account value and positions
- `/api/v1/health`: Health check endpoint

### Key Design Patterns

**Dependency Injection**: FastAPI dependencies for client and rebalancer instances
- `get_ibkr_client()`: Creates IBKR client with settings
- `get_rebalancer()`: Creates rebalancer with connected IBKR client

**Error Handling**: Comprehensive exception handling with logging via `loguru`

**Connection Management**: 
- Random client IDs to avoid conflicts with manual IBKR logins
- Automatic retry logic with exponential backoff
- Graceful degradation when IBKR is unavailable

### Data Flow

1. **Input**: Client sends allocation requests via `/calculate` or `/rebalance`
2. **Validation**: Pydantic models validate allocations sum to 1.0
3. **Connection**: IBKR client establishes connection to Gateway
4. **Data Gathering**: Fetch current account value, positions, and market prices
5. **Calculation**: Determine required buy/sell orders to reach target allocations
6. **Execution** (rebalance only): Submit orders to IBKR
7. **Response**: Return calculated orders or execution results

### Environment & Deployment

**Trading Modes**:
- `paper`: Paper trading for testing (default)
- `live`: Live trading with real money

**Docker Services**:
- `ibkr`: IBKR Gateway container (handles IBKR connection and 2FA)
- `rebalancer-api`: FastAPI application container

**Port Configuration**:
- 8000: FastAPI API
- 6080: IBKR Gateway web interface (noVNC)
- 8888: IBKR API port (paper trading)
- 7496: IBKR API port (live trading)

### Important Constraints

**Allocation Validation**: Target allocations must sum to exactly 1.0 (±0.01 tolerance)

**Order Execution Order**: Sells are executed before buys to ensure sufficient cash

**Connection Conflicts**: IBKR allows only one connection per user - manual logins will disconnect the service

**Synchronous Design**: All operations are synchronous; FastAPI handles async web layer but business logic is sync

### Recent Changes

**Major Refactor (2025-06-29): Fixed Event Loop Conflicts**
- **Implemented community-standard approach**: `nest-asyncio` + `--loop asyncio`
- **Applied nest_asyncio patch** to allow nested event loops within FastAPI
- **Forced asyncio loop** instead of uvloop to ensure nest_asyncio compatibility
- **Implemented singleton IBKR service** with FastAPI lifespan management  
- **Background connection management** with automatic retry logic
- **Simplified patterns** following community best practices

**Key Improvements:**
- Uses **proven community patterns** (nest_asyncio + asyncio loop)
- Persistent IBKR connection maintained in background
- No more mock/fallback data - real errors when IBKR unavailable
- Standard ib_async patterns with nest_asyncio handling event loop complexity
- New `/connection/status` endpoint for monitoring
- Graceful startup/shutdown with FastAPI lifespan events
- Compatible with most FastAPI + ib_async deployments