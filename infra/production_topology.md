# Production Infrastructure Topology & Architecture Specification

```
                    ┌─────────────────────────┐
                    │      Cloudflare Edge    │
                    │  (WAF, DDoS, SSL, CDN)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ Managed Ingress / LB   │
                    │ (TLS Termination, Routing)
                    └──────┬───────────┬──────┘
                           │           │
           ┌───────────────▼┐         ┌▼───────────────┐
           │ Next.js Replicas│         │ FastAPI API Replicas
           │ (SSR / Static)  │         │ (Autoscaled HPA)
           └────────────────┘         └───────┬────────┘
                                              │
         ┌──────────────────┬─────────────────┼─────────────────┐
         │                  │                 │                 │
┌────────▼────────┐ ┌───────▼──────┐ ┌────────▼────────┐ ┌──────▼────────┐
│ Celery Quick    │ │ Celery Deep  │ │ Celery Analysis │ │ Celery Reports│
│ Workers (HPA)   │ │ Workers (HPA)│ │ Workers (HPA)   │ │ Workers (HPA) │
└────────┬────────┘ └───────┬──────┘ └────────┬────────┘ └──────┬────────┘
         │                  │                 │                 │
         └──────────────────┼─────────────────┴─────────────────┘
                            │
       ┌────────────────────┼──────────────────┐
       │                    │                  │
┌──────▼───────────┐ ┌──────▼─────────┐ ┌──────▼─────────┐
│ Managed Postgres │ │ Managed Redis  │ │ Object Storage │
│ (Cloud SQL / RDS)│ │ (Memorystore / │ │ (GCS / S3      │
│ Multi-AZ Standby │ │  ElastiCache)  │ │  Dual-Region)  │
└──────────────────┘ └────────────────┘ └────────────────┘
```

## Managed Service Configurations

1. **Managed PostgreSQL**:
   - High-Availability Multi-AZ deployment
   - Automated nightly backups with 30-day point-in-time recovery (PITR)
   - Connection Pooling via PgBouncer (max 200 server connections)
   - SSL enforced (`sslmode=require`)

2. **Managed Redis Cluster**:
   - In-memory cache + Celery task broker with AOF enabled
   - Auto-failover with 2 read replicas

3. **Cloud Storage**:
   - S3 / GCS dual-region bucket for research snapshots, raw evidence, and PDF reports
   - Pre-signed URL access control (1-hour expiration)
   - Lifecycle policy: Archive raw evidence snapshots to Coldline after 90 days
