# 🏗️ System Architecture

## 📖 Overview

The IBKR Portfolio Rebalancer is a microservices-based system that automatically rebalances Interactive Brokers accounts based on target allocations from Zehnlabs. The system follows an event-driven architecture with robust error handling and retry mechanisms.

## 🧩 System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Zehnlabs      │    │  Event Broker   │    │     Redis       │
│   Events        │───▶│   (Ingestion)   │───▶│    Queue        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐             │
│ Management API  │    │ Event Processor │◀───────────┘
│  (Monitoring)   │    │  (Execution)    │
└─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  IBKR Gateway   │
                       │   + NoVNC       │
                       └─────────────────┘
```

### 🔧 Core Services

- **[Event Broker](services/event-broker.md)** - Ingests rebalancing events from Zehnlabs and queues them for processing
- **[Event Processor](services/event-processor.md)** - Processes queued events and executes trades through IBKR 
- **[Management Service](services/management-service.md)** - Provides health check, monitoring, and manual queue management API
- **[IBKR Gateway](services/ibkr-gateway.md)** - Interactive Brokers connection
- **[Infrastructure](services/infrastructure.md)** - Redis queues, NoVNC, and supporting services

## ⚙️ How It Works

### 🔄 Basic Flow
1. **Event Reception**: Zehnlabs publishes a rebalancing event for a strategy
2. **Queue Ingestion**: Event Broker receives the event and places it in Redis queue
3. **Event Processing**: Event Processor dequeues the event and fetches target allocations
4. **Trade Execution**: Required buy/sell orders are calculated and executed via IBKR Gateway
5. **Completion**: Event is marked complete, or requeued for retry if errors occur

### Data Flow
```
Zehnlabs Events ──▶ Event Broker ──▶ Redis Queue ──▶ Event Processor ──▶ IBKR Gateway
                                            ▲                   │
                                            │                   ▼
                                    Management API ◀──── Trade Results
```

## 🛡️ Reliability & Error Handling

### 💡 Design Principles
- **Decoupled Design**: Allows for reliably processing all events
- **Graceful Failures**: Temporary failures are retried and don't stop other events from processing  
- **Full Visibility**: Complete monitoring of queue status and processing health
- **Automatic Recovery**: Failed events automatically retry with appropriate delays

### Queue Architecture
- **Active Queue**: Events ready for immediate processing
- **Retry Queue**: Failed events waiting for retry
- **Deduplication**: Prevents duplicate processing using account+command keys
- **Retry Tracking**: Each event maintains count of processing attempts

### Error Recovery
When processing fails, events are automatically moved to a retry queue and retried later. This ensures:
- No events are lost
- Failed events don't block other processing
- System continues operating even during IBKR connectivity issues

## 🔒 Security Model

- **Network Isolation**: Services communicate via internal Docker network
- **Trading Modes**: Supports both paper trading and live trading modes
- **Credential Management**: IBKR credentials managed through environment variables

## 📊 Monitoring & Observability

The system provides comprehensive monitoring through:

- **Health Endpoints**: Real-time system health via Management API
- **Queue Metrics**: Active and retry event counts with processing statistics
- **Service Logs**: Structured JSON logging across all services with configurable levels
- **VNC Access**: Direct GUI access to IBKR Gateway for troubleshooting

## Deployment Architecture  

The system runs as Docker containers with:
- **Service Isolation**: Each component runs in its own container
- **Data Persistence**: Redis data and IBKR settings persist across restarts
- **Health Checks**: Automated health monitoring for all critical services
- **Log Management**: Logging with reasonable rotation and retention policies
- **Auto-restart**: Critical services automatically restart on failure