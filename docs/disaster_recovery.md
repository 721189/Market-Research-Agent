# Disaster Recovery & Business Continuity Architecture

## 1. Objectives & RTO / RPO Targets
- **Recovery Point Objective (RPO)**: < 5 minutes for relational state, 0 for financial ledger / Stripe events.
- **Recovery Time Objective (RTO)**: < 15 minutes to full API & worker operations.

---

## 2. Infrastructure Resilience Matrix

| Component | Architecture | Failure Mode | Recovery Procedure |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | Managed RDS / Cloud SQL with Multi-AZ Standby | Primary instance crash | Automated Multi-AZ failover (<60s) or Point-In-Time-Recovery (PITR) from WAL archives |
| **Redis Broker** | Managed Cluster with AOF persistence | Node crash | Sentinel / cluster replica promotion with queue preservation |
| **Object Storage** | S3 / GCS Dual-Region Buckets | Regional outage | Cross-region automatic replication with CDN failover |
| **Celery Workers** | Stateless containers with `acks_late=True` | SIGKILL / OOM | Unacknowledged messages instantly redelivered to healthy workers |
| **Stripe Billing** | Idempotency key & `stripe_event_id` tracking | Webhook replay | Deduplication logic returns `duplicate_ignored` with zero double-billing |

---

## 3. Point-in-Time Recovery (PITR) Runbook

1. **Verify WAL Archive Continuity**:
   ```bash
   pg_waldump /var/lib/postgresql/wal_archive/
   ```
2. **Execute Point-in-Time Restore**:
   ```bash
   pg_restore --target-time="2026-09-10 12:00:00 UTC" -d marketai_prod
   ```
3. **Validate Database Consistency**:
   - Verify `organizations`, `users`, `research_jobs`, and `usage_events` tables.
   - Run verification query:
     ```sql
     SELECT count(*) FROM research_jobs WHERE status = 'COMPLETED';
     ```

---

## 4. Webhook and Task Replay Runbook

- **Stripe Events**: Trigger event redelivery from Stripe Dashboard (`Developers > Webhooks > Resend event`).
- **Research Jobs**: Jobs in `FAILED` state due to transient provider rate limits can be requeued via `POST /api/v1/research/{task_id}/retry`.
