## IBKR API Rate Limits
- See rate-limits.md

## E2E Logging
- We need to have a way to see each even received by the event broker (assign GUID?), time received, and current status (Pending, Processed, Failed). 
- We should be able to drill down in Processed an Failed orders to see their detailed logs



- Secure management api?

- Management service root url returns version 1.0.0. Make it configurable.
- Queues `GET {{baseUrl}}/health` and `GET {{baseUrl}}/health/detailed` are redundant
- `POST {{baseUrl}}/queue/events` lacks duplicate check
- INFO logging is too verbose
