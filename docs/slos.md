# MarketAI Service Level Objectives (SLOs) & Reliability Framework

## 1. Synchronous API Tier

- **API Availability**: `99.9%` (Target: < 43 minutes downtime/month)
- **API p95 Latency**: `< 500 ms` for REST control plane operations
- **Job Enqueue Success Rate**: `> 99.9%`

---

## 2. Asynchronous Execution Pipeline Tier

Asynchronous background research operations have dedicated queue and execution SLOs rather than synchronous latency targets:

| Pipeline Stage | Target Queue Wait SLO (p95) | Target Execution Duration SLO (p95) | Completion Success Target |
| :--- | :--- | :--- | :--- |
| **Quick Research** (`research.quick`) | < 10 seconds | < 60 seconds | > 98.5% |
| **Deep Research** (`research.deep`) | < 30 seconds | < 300 seconds (5 min) | > 98.0% |
| **Analysis Pipeline** (`analysis`) | < 15 seconds | < 45 seconds | > 99.0% |
| **PDF Report Rendering** (`reports`) | < 20 seconds | < 30 seconds | > 99.0% |

---

## 3. Streaming and Notification SLOs

- **SSE Reconnect Event Recovery**: `< 5 seconds` with zero missed events via `Last-Event-ID` header.
- **Billing Webhook Success**: `> 99.99%` with idempotency deduplication.
