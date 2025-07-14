## IBKR API Rate Limits
- See rate-limits.md

## E2E Logging
- We need to have a way to see each even received by the event broker (assign GUID?), time received, and current status (Pending, Processed, Failed). 
- We should be able to drill down in Processed an Failed orders to see their detailed logs



- Secure management api?

- (Completed) Management service root url returns version 1.0.0. Make it configurable. 
- (Not an issue) `POST {{baseUrl}}/queue/events` lacks duplicate check
- (Completed) Ably key should come from .env (Realtime)
- (Completed) Rename ZEHNLABS_FINTECH_API_KEY to ALLOCATIONS_API_KEY.
- (Completed) Reformat .env and .env.example
- (Completed) Management API key to be removed and port only local
- INFO logging is too verbose
- Search warnings anf fix

