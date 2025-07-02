# IBKR ETF Pricing Strategy for Market Closure & Extended Hours

## Overview

This document outlines the comprehensive research findings and implementation plan for robust ETF pricing in the IBKR Portfolio Rebalancer application, specifically addressing pricing challenges when markets are closed and during pre/post Regular Trading Hours (RTH).

## Problem Statement

When markets are closed, some ETFs cannot retrieve snapshot prices through IBKR's API. This occurs due to:
- Market data subscription limitations (US Non-Consolidated Streaming Quotes package)
- Exchange venue closures
- Different API method behaviors during market hours vs. closure
- Need for pre/post RTH order creation

## Current Implementation Analysis

### Existing Pricing Methods (`rebalancer-api/app/services/ibkr_client.py`)

**Strengths:**
- Robust batch processing with `get_multiple_market_prices()`
- Comprehensive fallback logic: `marketPrice()` → `last` → `close`
- Connection management with retry logic
- Concurrency protection with `_market_data_lock`
- Error handling for individual symbol failures

**Limitations:**
- No market data type switching (always uses default live data)
- No frozen/snapshot data handling for closed markets
- No historical data fallback
- No pre/post RTH data support
- 2-second timeout may be insufficient for some scenarios

## IBKR Market Data Subscription Context

### Available Data with US Non-Consolidated Streaming Quotes

**Free Access:**
- Real-time streaming data for US stocks/ETFs from Cboe One and IEX
- Non-consolidated data (not NBBO)
- Snapshot quotes: $0.01 per request (with $1.00/month waiver)
- 100 concurrent market data lines

**Limitations:**
- No consolidated data (NBBO) without additional subscriptions
- Frozen data requires same subscriptions as real-time
- API access typically requires Level 1 subscription for most securities

## Market Data Types & Behavior

### IBKR API Market Data Types

1. **Live Data (Type 1)**: Real-time streaming (requires subscriptions)
2. **Frozen Data (Type 2)**: Last recorded data at market close (requires subscriptions + TWS v962+)
3. **Delayed Data (Type 3)**: 15-20 minute delayed (free for many instruments)
4. **Delayed-Frozen Data (Type 4)**: Delayed frozen for users without subscriptions

### Key Behaviors

- Frozen data only available for default tick types (no generic ticks)
- Error code 10167 indicates "venue closed"
- Market data type switches automatically back to real-time when markets reopen
- Snapshot requests timeout after 11 seconds
- Historical data has rate limits (60 requests per 10 minutes)

## Provided Code Analysis

### Code Evaluation

The provided `most_recent_price()` function implements a solid three-tier fallback strategy:

**Tier 1: Real-time Market Data**
```python
ib.reqMarketDataType(1)  # Real-time
ticker = ib.reqMktData(contract, '', snapshot=False)
```
- Subscribes to live data
- Waits for price updates with timeout
- Handles "venue closed" error (10167)

**Tier 2: Frozen Snapshot**
```python
ib.reqMarketDataType(2)  # Frozen
snap = ib.reqMktData(contract, '', snapshot=True)
```
- Falls back to last recorded prices
- Uses snapshot mode for quick retrieval

**Tier 3: Historical Data**
```python
bars = ib.reqHistoricalData(
    contract, endDateTime='', durationStr='30 m',
    barSizeSetting='1 min', whatToShow='TRADES',
    useRTH=0  # Include pre/post market
)
```
- Uses historical bars for extended hours
- `useRTH=0` includes pre/post market data
- Provides fallback when other methods fail

**Strengths:**
- Comprehensive fallback strategy
- Proper error handling for venue closure
- Event-driven architecture with callbacks
- Includes pre/post market data via historical bars

**Potential Issues:**
- Async complexity may not fit current sync architecture
- Historical data rate limits (60 requests/10 min)
- No batch processing capability
- May be overkill for simple rebalancing scenarios

## Pre/Post RTH Considerations

### Extended Hours Trading

**Pre-market:** 4:00 AM - 9:30 AM ET
**Post-market:** 4:00 PM - 8:00 PM ET

**Considerations:**
- Lower liquidity and wider spreads
- Not all ETFs trade in extended hours
- Different pricing mechanisms
- `useRTH=False` in historical data requests captures extended hours

### Order Placement Strategy

Users may create orders pre/post RTH, requiring:
- Accurate pricing during extended hours
- Order validation against available liquidity
- Proper order types (market orders may not execute in extended hours)

## Implementation Plan

### Phase 1: Enhanced Market Data Type Handling

**Objective:** Improve current pricing methods with market data type switching

**Changes to `ibkr_client.py`:**

1. **Add market data type management:**
   ```python
   async def _set_market_data_type(self, data_type: int):
       """Set market data type (1=live, 2=frozen, 3=delayed, 4=delayed-frozen)"""
       self.ib.reqMarketDataType(data_type)
       await asyncio.sleep(0.1)  # Allow type change to propagate
   ```

2. **Enhance price retrieval with fallback:**
   ```python
   async def get_robust_market_price(self, symbol: str) -> Optional[float]:
       """Get market price with market data type fallback"""
       # Try live data first
       try:
           await self._set_market_data_type(1)
           price = await self._get_single_price(symbol)
           if price: return price
       except Exception as e:
           logger.debug(f"Live data failed for {symbol}: {e}")
       
       # Fallback to frozen data
       try:
           await self._set_market_data_type(2)
           price = await self._get_single_price(symbol)
           if price: return price
       except Exception as e:
           logger.debug(f"Frozen data failed for {symbol}: {e}")
       
       # Final fallback to delayed data
       try:
           await self._set_market_data_type(3)
           price = await self._get_single_price(symbol)
           return price
       except Exception as e:
           logger.warning(f"All market data types failed for {symbol}: {e}")
           return None
   ```

3. **Batch processing with market data types:**
   - Implement batch processing for each market data type
   - Maintain performance while adding robustness
   - Group symbols by successful data type for efficiency

### Phase 2: Historical Data Fallback

**Objective:** Add historical data fallback for maximum robustness

**Implementation:**

1. **Add historical data service:**
   ```python
   async def get_historical_price(self, symbol: str, include_extended_hours: bool = True) -> Optional[float]:
       """Get most recent price from historical data"""
       try:
           contract = Stock(symbol, 'SMART', 'USD')
           bars = self.ib.reqHistoricalData(
               contract=contract,
               endDateTime='',
               durationStr='1 D',
               barSizeSetting='1 min',
               whatToShow='TRADES',
               useRTH=not include_extended_hours,
               formatDate=1
           )
           return bars[-1].close if bars else None
       except Exception as e:
           logger.error(f"Historical data request failed for {symbol}: {e}")
           return None
   ```

2. **Rate limiting for historical requests:**
   ```python
   @rate_limit(calls=50, period=600)  # 50 calls per 10 minutes
   async def _rate_limited_historical_request(self, symbol: str):
       return await self.get_historical_price(symbol)
   ```

### Phase 3: Market Hours Awareness

**Objective:** Optimize strategy based on market state

**Implementation:**

1. **Market hours detection:**
   ```python
   def is_market_open(self) -> bool:
       """Check if US equity markets are currently open"""
       # Implementation using market calendar or time-based logic
       pass
   
   def is_extended_hours(self) -> bool:
       """Check if currently in pre/post market hours"""
       pass
   ```

2. **Adaptive pricing strategy:**
   ```python
   async def get_adaptive_price(self, symbol: str) -> Optional[float]:
       """Get price using market-aware strategy"""
       if self.is_market_open():
           return await self.get_market_price(symbol)
       elif self.is_extended_hours():
           # Try frozen data first, then historical with extended hours
           return await self.get_robust_market_price(symbol)
       else:
           # Market closed - use frozen data or historical
           return await self.get_frozen_or_historical_price(symbol)
   ```

### Phase 4: Configuration & Monitoring

**Objective:** Make pricing strategy configurable and observable

**Configuration Options:**
```yaml
pricing:
  strategy: "adaptive"  # adaptive, live_only, frozen_fallback
  historical_fallback: true
  extended_hours_support: true
  timeout_seconds: 5
  max_retries: 3
  rate_limits:
    historical_requests_per_10min: 50
```

**Monitoring:**
- Track pricing method success rates
- Monitor rate limit usage
- Alert on pricing failures
- Log market data type usage

## Risk Considerations

### Data Quality Risks

- **Stale frozen data:** Prices may be from previous trading day
- **Extended hours volatility:** Wider spreads and lower liquidity
- **Rate limiting:** Historical data requests may be throttled

### Mitigation Strategies

- **Price validation:** Check price age and reasonableness
- **Order type selection:** Use limit orders for extended hours
- **Graceful degradation:** Fall back to manual pricing if all methods fail
- **Monitoring:** Alert on pricing anomalies

## Testing Strategy

### Unit Tests
- Test each pricing method individually
- Mock IBKR responses for different scenarios
- Test rate limiting functionality

### Integration Tests
- Test with real IBKR paper trading account
- Simulate market closed scenarios
- Test extended hours pricing

### Scenarios to Test
1. Normal market hours - live data
2. Market closed - frozen data fallback
3. Extended hours - historical data with useRTH=False
4. Data subscription issues - delayed data fallback
5. Rate limiting - proper error handling
6. Network issues - retry mechanisms

## Migration Strategy

### Phase 1 (Low Risk)
- Implement enhanced pricing alongside existing methods
- Add feature flag for new pricing strategy
- Test extensively in paper trading

### Phase 2 (Gradual Rollout)
- Enable new pricing for specific symbols
- Monitor performance and accuracy
- Gradual expansion to all symbols

### Phase 3 (Full Migration)
- Replace existing pricing methods
- Remove legacy code
- Full production deployment

## Conclusion

The proposed implementation provides a robust, multi-tiered approach to ETF pricing that addresses market closure scenarios while maintaining performance for the rebalancing application. The strategy balances complexity with reliability, ensuring orders can be created and executed effectively during both regular and extended trading hours.

The key innovation is the adaptive pricing strategy that automatically selects the most appropriate data source based on market conditions, providing consistent pricing availability while respecting IBKR's rate limits and subscription constraints.