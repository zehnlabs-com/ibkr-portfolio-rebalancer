#### Overview  
Interactive Brokers limits the traffic that can pass between your program and TWS/IB Gateway in order to protect their back-end systems and market-data vendors.  If you exceed a limit you will receive a **“pacing violation”** error (e.g. codes 162, 429, 10147 …) and in some cases the API connection will be blocked for 30 minutes.  
Below are the current public limits (TWS 10.27 / IB Gateway 10.27, July 2025).  All figures are *per client-id / per connection* unless stated otherwise.

---

#### 1. Global message-rate limit  
• **50 API messages per second** maximum in the **client → TWS** direction.  
  – A “message” is *any* outbound API call: `reqMktData`, `placeOrder`, `reqPositions`, heart-beat pings, etc.  
  – If the 50 msg/s ceiling is exceeded for two consecutive seconds TWS/Gateway will disconnect the session for ≈30 seconds and return error 429 (pacing violation).

---

#### 2. Market-data subscriptions (`reqMktData`)  
• **Concurrent streaming tickers** (snapshot requests are not counted):  
  – Non-professional account: **100**  
  – Non-professional after purchasing “Additional Market Data Lines”: up to **500**  
  – Professional account: **1 000**  
• **Subscription churn**: you may create/close **≤50 new tickers per second**.  
• Snapshot requests (`snapshot=True`) share the 50 msg/s global budget but do **not** count against the concurrent-ticker cap.

---

#### 3. Historical-data requests (`reqHistoricalData`)  
IB applies three overlapping throttles:  
1. **1 request / second** for the *same* contract.  
2. **6 requests / 2 seconds** across **all** contracts.  
3. **60 requests / 10 minutes** across **all** contracts.  
Exceeding any of the above triggers **error 162 – Historical data request pacing violation**.

---

#### 4. Real-time bars (`reqRealTimeBars`)  
• **Max concurrent real-time-bar streams:** **100** (these are 5-second bars delivered once per second).  
• They share the 50 msg/s global outbound budget.

---

#### 5. Tick-by-tick data (`reqTickByTickData`)  
• **Max concurrent tick-by-tick streams:** **60**.  
• Only **5 streams per underlying** are allowed.  
• Counts against the 50 msg/s global limit.

---

#### 6. Orders & cancels  
These calls also count toward the 50 msg/s bucket, but IB adds specialised limits as well:

| API call | Hard limit | Error code if breached |
|----------|------------|------------------------|
| `placeOrder` | 50 new orders / second | 10147 |
| `cancelOrder` | 20 cancels / second | 10217 |
| “Cancel-Replace” (modify) | 10 / second | 10150 |
| Cancel-to-new-order ratio | ≤60 cancels in any rolling minute **AND** cancels ≤55 % of new orders | 10151 |

A six-month rolling “excessive cancels” metric is also monitored; if the ratio stays above 40 % you may be charged per-cancel fees.

---

#### 7. Other notable limits  
• **Account updates** (`reqAccountUpdates`, `reqPositionsMulti` …) – each request counts toward 50 msg/s.  
• **Scanner subscriptions** – 10 simultaneous scanners; they each count as one active ticker.  
• **Fundamental data** (`reqFundamentalData`) – 60 requests / hour.  
• **News** (`reqNewsProviders`, `reqNewsArticle`) – 60 requests / hour.  
• **MarketDepth** (`reqMktDepth`) – 3 depth requests / symbol, 60 total.  

---

#### 8. Practical throttling recipe  

```python
import time
from collections import deque

MAX_MSG_PER_SEC = 48          # keep a safety cushion below 50
WINDOW_SEC       = 1.0
ts_queue         = deque()

def send_api_call(call, *args, **kwargs):
    # simple leaky-bucket throttler
    now = time.time()
    ts_queue.append(now)
    while ts_queue and now - ts_queue[0] > WINDOW_SEC:
        ts_queue.popleft()
    if len(ts_queue) >= MAX_MSG_PER_SEC:
        sleep_time = WINDOW_SEC - (now - ts_queue[0]) + 0.01
        time.sleep(max(0, sleep_time))
    call(*args, **kwargs)
```

This keeps you safely within 48 messages per second.

---

#### 9. Where to check the official numbers  
Interactive Brokers occasionally adjusts the caps.  The canonical source is:  
TWS / IB Gateway menu → API → “API Reference Guide” → “API → Programming/Connectivity → Pacing Violations & Limits”.  
Always confirm there after a new TWS/Gateway release.

---

#### Take-away  
1. **50 messages/sec is the master switch.**  
2. Historical data, tick-by-tick and order cancel/replace have their own sub-limits—memorise the 60/10-min historical rule.  
3. Build a client-side throttle so you *never* leave it to IB to enforce pacing.  

Stay inside those boundaries and your API connection will remain fast, stable and fee-free.