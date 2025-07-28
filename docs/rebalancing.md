# Rebalancing Algorithm

The rebalancer implements a sell-first portfolio rebalancing algorithm with cash reserve management and trading hours validation. When a rebalance event occurs, the system:

1. **Fetch Target Allocations**: Calls Zehnlabs API to get target allocations
2. **Get Current Positions**: Retrieves current holdings from IBKR
3. **Validate Trading Hours**: Checks trading hours for all symbols via IBKR contract details
4. **Cancel Existing Orders**: Cancels all pending orders to prevent conflicts (waits up to 60 seconds for confirmation)
5. **Calculate Target Positions**: Uses full account value for allocation calculations
6. **Generate Orders**: Creates buy/sell orders to reach target allocations
7. **Execute Sell Orders**: Submits sell orders first and waits for completion (with timeout)
8. **Get Cash Balance**: Retrieves actual cash balance after sells complete
9. **Execute Buy Orders**: Submits buy orders up to `Cash Balance - (Account Value × Configurable Reserve %)`

## Trading Hours Validation

Before executing any trades, the system validates that all symbols in the portfolio are within their respective trading hours:

### Process
1. **Fetch Contract Details**: Calls IBKR `reqContractDetails()` API for each symbol
2. **Extract Hours**: Gets `LiquidHours` (default) or `TradingHours` (when extended hours enabled)
3. **Parse Schedule**: Parses IBKR trading hours format (`YYYYMMDD:HHMM-YYYYMMDD:HHMM`)
4. **Validate Time**: Checks current time against each symbol's schedule
5. **All-or-None**: If ANY symbol is outside hours, entire rebalance is delayed

### Configuration
- **Extended Hours**: Set `EXTENDED_HOURS_ENABLED=true` to use extended trading hours
- **Hours Selection**: 
  - `EXTENDED_HOURS_ENABLED=false` → Uses `LiquidHours` (regular market hours)
  - `EXTENDED_HOURS_ENABLED=true` → Uses `TradingHours` (includes pre/post market)

### Delayed Execution
When symbols are outside trading hours:
1. **Calculate Next Window**: Determines earliest next trading session start
2. **Queue Event**: Places event in `delayed_execution_set` Redis queue with execution timestamp
3. **Background Processing**: Delayed processor checks every minute for ready events
4. **Automatic Retry**: Event automatically returns to main queue when trading hours begin

### Timezone Handling
- **System Timezone**: All containers run in `America/New_York` timezone
- **IBKR Times**: IBKR API returns times in `US/Eastern` (equivalent to America/New_York)
- **No Conversion**: No timezone conversion needed as both use same timezone with DST

## Order Cancellation

Before placing new rebalancing orders, the system automatically cancels all existing pending orders for the account to prevent duplicate or conflicting trades. 

**Important**: If existing orders cannot be cancelled within 60 seconds, the rebalancing process will fail with an error and retried later. This prevents the system from placing new orders when old orders are still pending, which could result in overtrading or unintended positions. 

**Behavior:**
1. **Sell Orders Placed**: System places all sell orders and collects their order IDs
2. **Status Polling**: Polls order status every 2 seconds for up to 60 seconds (configurable)
3. **Success Case**: All sell orders complete → Buy orders execute with updated cash balance
4. **Timeout Case**: After 60 seconds → Event fails → Automatic retry mechanism triggers
5. **Retry Handling**: Next attempt starts fresh with current positions/cash state

## Cash Reserve System

The system maintains a configurable cash reserve applied after sell orders complete to improve order fill rates and handle market volatility:

**Purpose:**
- **Slippage and Fees**: Provides cushion for slippage and trading fees
- **Risk Management**: Prevents over-leveraging the account

**Configuration:**
Each account can have its own reserve percentage configured in `accounts.yaml`:

```yaml
accounts:
  - account_id: "DU123456"
    rebalancing:
      cash_reserve_percent: 1.0  # 1% reserve (default 0.0)
```

**Validation:**
- **Range**: 0% to 100% (values outside this range default to 0%)
- **Default**: 0% if not specified or invalid

**Reserve Calculation:**
The cash reserve is calculated based on **total account value**, not available cash:

**Example:**
- Account Value: $100,000
- Reserve: 2% of account value = $2,000
- Available Cash After Sells: $85,000
- Cash Available for Buy order: $85,000 - $2,000 = $83,000