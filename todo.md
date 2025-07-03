## IBKR API Rate Limits
- See rate-limits.md

## Failed Order Handling
- Failed orders include:
    - Orders that don't execute by COB because they were received too late
    - Orders that failed in the middle of execution
- Suggested Implementation:    
    - Event broker enqueues to a Redis Queue instead of communicating with rebalancer over API
    - Rebalancer sequentially dequeues and processes account rebalances
    - Failed or unexecuted orders that do not execute by close of market will be executed the next day
    - Get rid of Fast Api, all the complex event loop, async, and thread management code.
    - Get rid of robust pricing logic. This was there only to suport the use case that event broker could send an event after market close. If that happens, IBKR does not return current snapshot prices of certain symbols. However, if we go the queueing route, we can process the queue only during market hours thereby no need for ronust pricing logic.
    - For orders processed during the day we can by default use market orders, and for orders received in the last hour before the market close we can automatically use Market On Close orders. We can then remove the default_order_type logic.

## E2E Logging
- We need to have a way to see each even received by the event broker (assign GUID?), time received, and current status (Pending, Processed, Failed). 
- We should be able to drill down in Processed an Failed orders to see their detailed logs