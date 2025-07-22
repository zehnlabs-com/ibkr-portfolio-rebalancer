# Rebalancing Algorithm

The rebalancer implements a sell-first portfolio rebalancing algorithm with cash reserve management. When a rebalance event occurs, the system:

1. **Fetch Target Allocations**: Calls Zehnlabs API to get target allocations
2. **Get Current Positions**: Retrieves current holdings from IBKR
3. **Cancel Existing Orders**: Cancels all pending orders to prevent conflicts (waits up to 60 seconds for confirmation)
4. **Calculate Target Positions**: Uses full account value for allocation calculations
5. **Generate Orders**: Creates buy/sell orders to reach target allocations
6. **Execute Sell Orders**: Submits sell orders first and waits for completion (with timeout)
7. **Get Cash Balance**: Retrieves actual cash balance after sells complete
8. **Execute Buy Orders**: Submits buy orders up to `Cash Balance - (Account Value × Configurable Reserve %)`

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
- account_id: "DU123456"
  rebalancing:
    cash_reserve_percent: 1.0  # 1% reserve (default)
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