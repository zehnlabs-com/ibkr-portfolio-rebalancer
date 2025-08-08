# Portfolio Dashboard Technical Specification

## Version: 1.0
## Date: January 2025
## Author: System Architect

---

## Executive Summary

This specification details the implementation of a comprehensive portfolio monitoring dashboard for the IBKR Portfolio Rebalancer system. The dashboard will provide real-time portfolio monitoring, account management, and system administration capabilities for several trading accounts without impacting the existing event-driven rebalancing architecture.

### Key Design Decisions
- **No IBKR Service Extraction**: Maintain IBKRClient within event-processor to preserve low-latency trading
- **Redis-Only Caching**: No additional database required for initial implementation
- **Management Service Extension**: Leverage existing service instead of creating new API service
- **Docker Socket Integration**: Direct container management and log access
- **Background Data Collection**: Asynchronous collection to avoid blocking trading operations

---

## High-Level Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Dashboard UI                       │
│                          (Port: 3000)                           │
└───────────────────┬─────────────────────────────────────────────┘
                    │ HTTP/WebSocket
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Management Service (Extended)                │
│                          (Port: 8000)                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  Dashboard   │   Docker     │   Config     │   Existing    │ │
│  │   Handlers   │  Handlers    │  Handlers    │   Handlers    │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
└────────┬──────────────────┬─────────────────────────────────────┘
         │                  │
         │ Redis            │ Docker Socket
         ▼                  ▼
┌─────────────────┐  ┌──────────────┐
│      Redis       │  │    Docker    │
│  Cache & Queue   │  │   Daemon     │
└─────────────────┘  └──────────────┘
         ▲
         │ Data Collection
         │
┌─────────────────────────────────────────────────────────────────┐
│                        Event Processor                           │
│  ┌────────────────────────────┬────────────────────────────┐   │
│  │    Data Collector Service  │    Existing Components      │   │
│  │      (New Background)      │    (Unchanged)              │   │
│  └────────────────────────────┴────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Portfolio Data Collection**
   - Event Processor → Data Collector → Redis Cache
   - Collection Interval: 5 minutes (configurable)
   - Cache TTL: 300 seconds for positions/values

2. **Dashboard Data Access**
   - React UI → Management Service → Redis Cache (read-only)
   - Real-time updates via WebSocket subscriptions

3. **System Management**
   - React UI → Management Service → Docker Socket
   - Container control, log access, health monitoring

---

## IMPORTANT: Implementation Guidelines
- No backward compatibility required
- This is a financial application with legal consequences. Implementation MUST never have any fallback code that masks errors or other issues
- It is IMPORTANT that instead of making assumptions the developer always verifies information
- The implementation should prioritize Single Responsibility Principle
- If any out-of-scope design issues or vulnerabilities discovered during implementation, they must be added to /docs/issues.md
- If any new ideas of suggesstion come up during implementation they must be added to /docs/suggesstions.md
- If any item could not be completed due to conflicting or incomplete information they must be added to /docs/todo.md
- In dashboard all the latest node version and dependency versions should be used

## Component Specifications

### 1. Event Processor Extensions

#### 1.1 Data Collector Service

**Location**: `event-processor/app/services/data_collector_service.py`

**Class**: `DataCollectorService`

**Responsibilities**:
- Periodic collection of portfolio data for all accounts in accounts.yaml
- Last close net liquidation value capture for P&L calculation  
- Cache management in Redis

**Key Methods**:
```python
async def start_collection_tasks()
async def collect_all_accounts()  # Every 5 minutes - collects all accounts in accounts.yaml
async def collect_account_data(account_id: str)  # Single atomic operation
async def collect_last_close_netliq()  # After market close daily
async def load_accounts_config()  # Read accounts.yaml to get list of accounts
```

**Redis Keys Structure**:
```
# Single JSON document per account
account_data:{account_id}        # Complete account data JSON, TTL: configurable (default 300s)

# Last close net liquidation (separate for daily persistence)
last_close_netliq:{account_id}:{date}  # Net liquidation value at close, TTL: 86400s

# System metadata  
collection:status                # Current collector status
collection:last_run              # Last successful collection timestamp
```

**Integration Point**:
```python
# event-processor/app/core/application_service.py
class ApplicationService:
    async def start(self):
        # ... existing code ...
        
        # Start data collector service
        data_collector = DataCollectorService(
            self.service_container.get_ibkr_client(),
            redis_client
        )
        asyncio.create_task(data_collector.start_collection_tasks())
```

---

### 2. Management Service Extensions

#### 2.1 Dashboard Handlers

**Location**: `management-service/app/handlers/dashboard_handlers.py`

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/overview` | System-wide overview |
| GET | `/api/dashboard/accounts` | All accounts summary |
| GET | `/api/dashboard/accounts/{account_id}` | Single account details |
| GET | `/api/dashboard/accounts/{account_id}/positions` | Account positions |
| GET | `/api/dashboard/accounts/{account_id}/pnl` | Today's P&L |
| WS | `/api/dashboard/stream` | Real-time updates WebSocket |

**Response Models**:
```python
# management-service/app/models/dashboard_models.py

class Position(BaseModel):
    symbol: str
    quantity: float
    market_value: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float

class AccountData(BaseModel):
    account_id: str
    enabled: bool  # Read from accounts.yaml
    current_value: float
    last_close_netliq: float  # Yesterday's closing net liquidation value
    todays_pnl: float  # current_value - last_close_netliq
    todays_pnl_percent: float  # ((current_value - last_close_netliq) / last_close_netliq) * 100
    positions: List[Position]
    last_update: datetime
    
    @property
    def positions_count(self) -> int:
        return len(self.positions)
```

#### 2.2 Docker Management Handlers

**Location**: `management-service/app/handlers/docker_handlers.py`

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/containers` | List all containers |
| GET | `/api/containers/{name}/stats` | Container resource usage |
| GET | `/api/containers/{name}/logs` | Container logs |
| POST | `/api/containers/{name}/start` | Start container |
| POST | `/api/containers/{name}/stop` | Stop container |
| POST | `/api/containers/{name}/restart` | Restart container |
| WS | `/api/containers/{name}/logs/stream` | Stream logs via WebSocket |

**Dependencies**:
```python
# management-service/requirements.txt
docker==7.1.0  # Add for Docker management (latest version, Python 3.12 compatible)
websockets==15.0.1  # Add for WebSocket support (latest version, Python 3.12 compatible)
```

```json
# dashboard-ui/package.json additions
{
  "dependencies": {
    "express": "^5.1.0",
    "http-proxy-middleware": "^3.0.5",
    "react-admin": "^5.8.0",
    "@mui/material": "^7.3.1",
    "@mui/icons-material": "^7.3.1",
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.0",
    "recharts": "^2.15.0",
    "react-use-websocket": "^4.13.0",
    "sass": "^1.90.0"
  },
  "devDependencies": {
    "vite": "^7.0.6"
  },
  "scripts": {
    "build": "vite build",
    "serve": "node server.js",
    "dev": "vite"
  },
  "engines": {
    "node": ">=20.19.0"
  }
}
```

#### 2.3 Configuration Management Handlers

**Location**: `management-service/app/handlers/config_handlers.py`

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/env` | Get .env configuration |
| PUT | `/api/config/env` | Update .env configuration |
| GET | `/api/config/accounts` | Get accounts.yaml |
| PUT | `/api/config/accounts` | Update accounts.yaml |
| POST | `/api/config/restart-services` | Restart affected services |

**File Handling**:
- Mount configurations as read-write volumes
- Use TypeScript libraries (js-yaml) for YAML parsing/serialization
- Audit log all configuration changes
- Account enable/disable triggers event-broker restart

---

### 3. React Dashboard UI

#### 3.1 Technology Stack

**Framework**: React-admin with TypeScript
**UI Library**: Material-UI (built into react-admin)
**Data Provider**: Custom data provider for management service API
**Charts**: Recharts (integrated into dashboard widgets)
**WebSocket**: react-use-websocket (for real-time portfolio updates)
**Build Tool**: Vite
**Server**: Express.js with API proxy
**Theme**: Material Design + ZehnLabs brand colors
**Real-time**: WebSocket integration with react-admin patterns

**Package Structure**:
```
dashboard-ui/
├── src/
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── PortfolioOverview.tsx    # Custom portfolio dashboard
│   │   │   ├── AccountCard.tsx          # Portfolio account widgets
│   │   │   └── SystemHealthCards.tsx    # System status widgets
│   │   ├── accounts/
│   │   │   ├── AccountList.tsx          # React-admin list
│   │   │   ├── AccountEdit.tsx          # React-admin edit form
│   │   │   └── AccountCreate.tsx        # React-admin create form
│   │   ├── containers/
│   │   │   ├── ContainerList.tsx        # Docker container management
│   │   │   └── ContainerActions.tsx     # Start/stop/restart actions
│   │   ├── logs/
│   │   │   ├── LogList.tsx              # Log viewer with filtering
│   │   │   └── LogDetail.tsx            # Individual log details
│   │   └── config/
│   │       ├── EnvConfigEdit.tsx        # Environment variables editor
│   │       └── ServiceRestart.tsx       # Service restart controls
│   ├── providers/
│   │   ├── dataProvider.ts              # React-admin data provider
│   │   └── websocketProvider.ts         # Real-time updates integration
│   ├── theme/
│   │   ├── zehnlabsTheme.ts            # Material-UI + ZehnLabs theme
│   │   └── customStyles.scss            # Additional styling
│   ├── hooks/
│   │   ├── useRealTimeData.ts           # WebSocket integration
│   │   └── usePortfolioData.ts          # Portfolio-specific hooks
│   ├── Dashboard.tsx           # Custom dashboard page
│   └── App.tsx                 # React-admin app configuration
├── server.js              # Express server with API proxy
├── Dockerfile
└── package.json
```

#### 3.2 ZehnLabs Theme Configuration

**Color Palette** (based on ZehnLabs branding):
```css
:root {
  /* Primary Colors (ZehnLabs brand) */
  --primary: #2975ba;           /* Main ZehnLabs blue */
  --primary-light: #4a8cd4;    /* Lighter variant */
  --primary-dark: #1e5a94;     /* Darker variant */
  
  /* Accent Colors */
  --accent: #1fc5d1;           /* ZehnLabs cyan */
  --accent-light: rgba(31, 197, 209, 0.45); /* Translucent cyan */
  
  /* Financial Data Colors */
  --success: #52c41a;          /* Green for profits */
  --error: #ff4d4f;            /* Red for losses */
  --warning: #faad14;          /* Orange for warnings */
  
  /* Background & Surface */
  --background: #ffffff;        /* Clean white */
  --surface: #fafafa;          /* Light gray surfaces */
  --overlay: rgba(255,255,255,0.85); /* Translucent overlays */
  --border: #e8e8e8;           /* Light borders */
}
```

**Material-UI Theme Configuration**:
```typescript
// theme/zehnlabsTheme.ts
import { createTheme } from '@mui/material/styles';

export const zehnlabsTheme = createTheme({
  palette: {
    primary: {
      main: '#2975ba',        // ZehnLabs blue
      light: '#4a8cd4',
      dark: '#1e5a94',
    },
    secondary: {
      main: '#1fc5d1',        // ZehnLabs cyan
      light: 'rgba(31, 197, 209, 0.45)',
    },
    success: { main: '#52c41a' },
    error: { main: '#ff4d4f' },
    warning: { main: '#faad14' },
    background: {
      default: '#ffffff',
      paper: '#fafafa',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: 16,
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          textTransform: 'none',
        },
      },
    },
  },
});
```

**Dashboard-Specific Styling**:
```scss
// theme/customStyles.scss
.portfolio-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 197, 209, 0.2);
}

.account-header {
  background: linear-gradient(135deg, #2975ba 0%, #1fc5d1 100%);
  color: white;
  padding: 16px;
  border-radius: 8px 8px 0 0;
}

.metric-positive { color: #52c41a; font-weight: 600; }
.metric-negative { color: #ff4d4f; font-weight: 600; }

.data-visualization {
  background: rgba(31, 197, 209, 0.05);
  border-left: 4px solid #2975ba;
  padding: 16px;
}

// React-admin customizations
.RaLayout-content {
  padding: 24px;
}

.RaList-main {
  .MuiTableHead-root {
    background-color: #fafafa;
  }
}
```

#### 3.3 React-Admin Resources & Features

**Portfolio Dashboard** (Custom dashboard page):
- Real-time portfolio overview with WebSocket updates
- Account cards showing current value and today's P&L ($ and % change from yesterday's close)
- System health indicators
- Recent activity feed

**Account Management** (React-admin resource):
```typescript
<Resource 
  name="accounts" 
  list={AccountList}           // List all accounts with enable/disable
  edit={AccountEdit}           // Edit account configuration
  create={AccountCreate}       // Add new accounts
/>
```
- CRUD operations for accounts
- Enable/disable toggle
- Account configuration forms
- Built-in filtering and sorting

**Container Management** (React-admin resource):
```typescript
<Resource 
  name="containers" 
  list={ContainerList}         // List all services with status
  actions={ContainerActions}   // Start/stop/restart actions
/>
```
- Service status monitoring
- Container control actions
- Resource usage display
- Health check indicators

**Log Viewer** (React-admin resource):
```typescript
<Resource 
  name="logs" 
  list={LogList}               // Searchable log entries
  show={LogDetail}             // Individual log details
/>
```
- Real-time log streaming
- Built-in filtering and search
- Service-specific log views
- Export capabilities

**Configuration Management** (Custom pages):
- Environment variables editor
- Service restart controls
- Configuration validation

#### 3.4 Data Provider Implementation

**Custom Data Provider** for Management Service API:
```typescript
// providers/dataProvider.ts
import { DataProvider } from 'react-admin';

export const dataProvider: DataProvider = {
  // Account management
  getList: (resource, params) => {
    if (resource === 'accounts') {
      return fetch('/api/dashboard/accounts').then(res => ({
        data: res.accounts,
        total: res.accounts.length
      }));
    }
    if (resource === 'containers') {
      return fetch('/api/containers').then(res => ({
        data: res.containers,
        total: res.containers.length
      }));
    }
    // ... other resources
  },
  
  getOne: (resource, params) => {
    if (resource === 'accounts') {
      return fetch(`/api/dashboard/accounts/${params.id}`);
    }
  },
  
  update: (resource, params) => {
    if (resource === 'accounts') {
      // Update accounts.yaml
      return fetch('/api/config/accounts', {
        method: 'PUT',
        body: JSON.stringify(params.data)
      });
    }
  },
  
  create: (resource, params) => {
    if (resource === 'accounts') {
      // Add new account to accounts.yaml
      return fetch('/api/config/accounts', {
        method: 'PUT',
        body: JSON.stringify(params.data)
      });
    }
  },
  
  // Custom actions for containers
  containerAction: (containerId: string, action: string) => {
    return fetch(`/api/containers/${containerId}/${action}`, {
      method: 'POST'
    });
  }
};
```

**Real-time Integration**:
```typescript
// hooks/useRealTimeData.ts
import { useWebSocket } from 'react-use-websocket';
import { useDataProvider, useRefresh } from 'react-admin';

export const useRealTimePortfolio = () => {
  const refresh = useRefresh();
  
  useWebSocket('/api/dashboard/stream', {
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'account_update') {
        // Trigger refresh for specific account
        refresh();
      }
    }
  });
};
```

---

## Implementation Plan

### Phase 1: Foundation
1. **Event Processor Modifications**
   - Implement DataCollectorService
   - Add background collection tasks
   - Set up Redis caching structure
   - Test data collection without blocking trading

2. **Management Service Setup**
   - Add docker-py dependency
   - Mount Docker socket and config files
   - Create base handler classes
   - Set up WebSocket support

### Phase 2: API Development
1. **Dashboard API Endpoints**
   - Implement all GET endpoints for portfolio data
   - Add WebSocket streaming for real-time updates
   - Create response models and serializers

2. **Docker Management API**
   - Container listing and stats
   - Log retrieval and streaming
   - Container lifecycle management
   - Safety checks for critical services

3. **Configuration API**
   - File reading and parsing
   - Validation
   - Update mechanisms with audit logging

### Phase 3: React-Admin UI Development
1. **React-Admin Setup**
   - Initialize project with Vite + React-Admin
   - Configure TypeScript and ESLint
   - Set up ZehnLabs theme with Material-UI
   - Configure Express.js server with API proxy
   - Implement custom data provider

2. **Core Resources**
   - Account management (List/Edit/Create components)
   - Container management (List with actions)
   - Log viewer (List/Detail components)
   - Configuration management (Custom forms)

3. **Custom Dashboard**
   - Portfolio overview with real-time updates
   - Account cards with today's P&L display ($ change and % change from yesterday's close)
   - System health widgets
   - WebSocket integration for live data

### Phase 4: Integration & Testing
1. **Integration Testing**
   - End-to-end data flow verification
   - WebSocket connection stability
   - Configuration update testing
   - Service restart coordination

2. **Performance Testing**
   - Redis cache performance
   - UI responsiveness
   - Memory usage monitoring

### Phase 5: Deployment
1. **Docker Configuration**
   - Update docker-compose.yaml
   - Configure Express.js server for React app
   - Set up health checks
   - Volume mount verification

2. **Documentation**
   - User guide for dashboard
   - Admin procedures
   - Troubleshooting guide
   - API documentation

---

## Technical Considerations

### Performance Optimizations

1. **Data Collection Strategy**
   ```python
   # Batch collection for efficiency
   async def collect_all_accounts():
       accounts = await get_enabled_accounts()
       
       # Chunk accounts to avoid rate limits
       for chunk in chunks(accounts, 5):
           await asyncio.gather(*[
               collect_account_data(acc) for acc in chunk
           ])
           await asyncio.sleep(1)  # Rate limit protection
   
   async def collect_account_data(self, account_id: str):
       """Single atomic operation per account"""
       # Fetch all data concurrently
       positions, net_liq, orders = await asyncio.gather(
           self.ibkr_client.get_positions(account_id),
           self.ibkr_client.get_account_value(account_id),  # Returns net liquidation value
           self.get_account_orders(account_id)
       )
       
       # Get yesterday's closing net liq
       yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
       last_close_key = f"last_close_netliq:{account_id}:{yesterday}"
       last_close_netliq = await redis.get(last_close_key)
       
       # Calculate P&L
       if last_close_netliq:
           last_close_netliq = float(last_close_netliq)
           todays_pnl = net_liq - last_close_netliq
           todays_pnl_percent = (todays_pnl / last_close_netliq) * 100 if last_close_netliq else 0
       else:
           todays_pnl = 0
           todays_pnl_percent = 0
           last_close_netliq = net_liq  # Use current as fallback
       
       # Build single JSON document
       account_data = {
           "account_id": account_id,
           "current_value": net_liq,
           "last_close_netliq": last_close_netliq,
           "todays_pnl": todays_pnl,
           "todays_pnl_percent": todays_pnl_percent,
           "positions": positions,
           "orders": orders,
           "last_update": datetime.now().isoformat()
           # ... complete account state
       }
       
       # Single Redis operation
       await redis.setex(
           f"account_data:{account_id}", 
           ttl, 
           json.dumps(account_data)
       )
   ```

2. **Simplified API Pattern**
   ```python
   @app.get("/api/dashboard/accounts/{account_id}")
   async def get_account_data(account_id: str):
       data = await redis.get(f"account_data:{account_id}")
       if not data:
           raise HTTPException(404, "Account data not found")
       return json.loads(data)  # Direct return - no aggregation needed!
   ```

3. **WebSocket Optimization**
   ```python
   # Send complete account state (simplified)
   await websocket.send_json({
       "type": "account_update",
       "account_id": account_id,
       "data": account_data  # Complete JSON document
   })
   
   # Client handles full state replacement
   ```

### Error Handling

1. **Graceful Degradation**
   - Show cached data when fresh data unavailable
   - Handle IBKR connection failures
   - Queue retry for failed collections
   - Fallback UI states

2. **Circuit Breaker Pattern**
   ```python
   class CircuitBreaker:
       def __init__(self, failure_threshold=5, timeout=60):
           self.failure_count = 0
           self.failure_threshold = failure_threshold
           self.timeout = timeout
           self.last_failure_time = None
           self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
   ```

### Monitoring & Observability

1. **Health Checks**
   ```python
   @app.get("/api/health/dashboard")
   async def dashboard_health():
       return {
           "redis_connected": await check_redis(),
           "docker_accessible": await check_docker(),
           "last_collection": await get_last_collection_time(),
           "accounts_monitored": await get_monitored_accounts_count()
       }
   ```

---

## Appendix

### A. Redis Key Reference

```
# Portfolio Data (Simplified!)
account_data:{account_id}           # Complete account JSON document, TTL: configurable (300s)

# Last close net liquidation (separate for daily persistence)
last_close_netliq:{account_id}:{date}     # Net liquidation value at close, TTL: 86400s

# System metadata
accounts:enabled                    # Set of enabled accounts
collection:status                   # Running/Stopped
collection:last_run                 # Timestamp

# Configuration cache (optional)
config:env                          # Cached .env
config:accounts                     # Cached accounts.yaml
config:last_modified                # Timestamp
```

### B. Docker Compose Additions

```yaml
# docker-compose.yaml additions

services:
  management-service:
    volumes:
      - ./management-service/logs:/app/logs
      - ./accounts.yaml:/app/config/accounts.yaml:rw
      - ./.env:/app/config/.env:rw
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      DOCKER_HOST: unix:///var/run/docker.sock      

  dashboard-ui:
    container_name: dashboard-ui
    build: ./dashboard-ui
    ports:
      - "0.0.0.0:3000:3000"
    environment:
      - NODE_ENV=production
      - API_BASE_URL=http://management-service:8000
    depends_on:
      - management-service
    networks:
      - ibkr-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    volumes:
      - /etc/localtime:/etc/localtime:ro
```

### C. Configuration Files

**Event Processor Config** (`event-processor/config.yaml`):
```yaml
# Add dashboard data collection settings
data-collection:  
  collection_interval: 300  # seconds - how often to collect data
  cache_ttl: 300           # seconds - TTL for account_data:{account_id} keys
  market_close_time: "16:00"  # Market close time for net liq snapshots
  
# Existing config sections remain unchanged
processing:
  max_concurrent_events: 3
  # ... existing settings
```

**Management Service Config** (`management-service/config.yaml` - new file):
```yaml
dashboard:
  log_retention_hours: 24
  enable_config_edit: true
  enable_service_control: true
  protected_services:
    - management-service
    - redis
    - ibkr-gateway

docker:
  socket_path: /var/run/docker.sock
  timeout: 10

api:
  cors_origins: ["*"]
  max_log_lines: 1000
```

**Dashboard UI Config** (`dashboard-ui/config.json`):
```json
{
  "api": {
    "baseUrl": "/api",
    "websocketUrl": "/api/dashboard/stream"
  },
  "ui": {
    "refreshInterval": 30000,
    "theme": "light",
    "pageSize": 50
  },
  "features": {
    "configEdit": true,
    "serviceControl": true,
    "logViewer": true
  }
}
```

---

## Conclusion

This specification provides a comprehensive blueprint for adding a portfolio monitoring dashboard to the IBKR Portfolio Rebalancer system. The design prioritizes:

1. **Zero impact on trading operations** - Trading logic remains unchanged
2. **Rapid development** - React-admin eliminates 70% of custom UI code
3. **Maintainability** - Professional, battle-tested components

The phased approach allows for incremental delivery and testing, reducing risk and ensuring system stability throughout the development process.