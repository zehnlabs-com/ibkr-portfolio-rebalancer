# System Architecture

## Overview

The IBKR Portfolio Rebalancer is a microservices-based system that automatically rebalances Interactive Brokers accounts based on target allocations from Zehnlabs. The system follows an event-driven architecture with robust error handling and retry mechanisms.

## System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Zehnlabs      │    │  Event Broker   │    │     Redis       │
│   Events        │───▶│   (Ingestion)   │───▶│    Queue        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐           │
│ Management API  │    │ Event Processor │◀──────────┘
│  (Monitoring)   │    │  (Execution)    │
└─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  IBKR Gateway   │
                       │   + NoVNC       │
                       └─────────────────┘
```

### Core Services

- **[Event Broker](services/event-broker.md)** - Ingests rebalancing events from Zehnlabs and queues them for processing
- **[Event Processor](services/event-processor.md)** - Processes queued events and executes trades through IBKR 
- **[Management Service](services/management-service.md)** - Provides monitoring API and manual queue management
- **[IBKR Gateway](services/ibkr-gateway.md)** - Interactive Brokers connection with VNC access for troubleshooting
- **[Infrastructure](services/infrastructure.md)** - Redis queues, NoVNC, and supporting services

## How It Works

### Basic Flow
1. **Event Reception**: Zehnlabs publishes a rebalancing event for a specific account
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

## Reliability & Error Handling

### Design Principles
- **Zero Event Loss**: All events are retained and retried until successful
- **Graceful Failures**: Temporary failures don't stop other events from processing  
- **Full Visibility**: Complete monitoring of queue status and processing health
- **Automatic Recovery**: Failed events automatically retry with appropriate delays

### Queue Architecture
- **Active Queue**: Events ready for immediate processing
- **Delayed Queue**: Failed events waiting for retry with timestamps
- **Deduplication**: Prevents duplicate processing using account+command keys
- **Retry Tracking**: Each event maintains count of processing attempts

### Error Recovery
When processing fails, events are automatically moved to a delayed queue and retried later. This ensures:
- No events are lost
- Failed events don't block other processing
- System continues operating even during IBKR connectivity issues
- Operators have full visibility into problem events

## Security Model

- **Network Isolation**: Services communicate via internal Docker network
- **Trading Modes**: Supports both paper trading (safe) and live trading modes
- **Credential Management**: IBKR credentials managed through environment variables

## Monitoring & Observability

The system provides comprehensive monitoring through:

- **Health Endpoints**: Real-time system health via Management API
- **Queue Metrics**: Active and delayed event counts with processing statistics
- **Service Logs**: Structured JSON logging across all services with configurable levels
- **VNC Access**: Direct GUI access to IBKR Gateway for troubleshooting
- **Event Tracking**: Complete audit trail of event processing and retry attempts

## Deployment Architecture  

The system runs as Docker containers with:
- **Service Isolation**: Each component runs in its own container
- **Data Persistence**: Redis data and IBKR settings persist across restarts
- **Health Checks**: Automated health monitoring for all critical services
- **Log Management**: Centralized logging with rotation and retention
- **Auto-restart**: Services automatically restart on failure