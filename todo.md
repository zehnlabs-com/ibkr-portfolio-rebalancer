## IBKR API Rate Limits
- See rate-limits.md

## Failed Order Handling
- Failed orders include:
    - Orders that don't execute by COB because they were received too late
    - Orders that failed in the middle of execution
- Suggested Implementation:    
    - Event broker enqueues to a Redis Queue instead of communicating with rebalancer over API
    - Rebalancer sequentially dequeues and processes account rebalances
    - Failed or unexecuted orders will be executed the next day
    - Get rid of Fast Api, all the complex event loop and thread management code, robust pricing, etc.
    - Orders are always sent to broker during market hours

## E2E Logging
- We need to have a way to see each even received by the event broker (assign GUID?), time received, and current status (Pending, Processed, Failed). 
- We should be able to drill down in Processed an Failed orders to see their detailed logs