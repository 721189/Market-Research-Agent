# MarketAI Production Architecture

This document describes the final enterprise-grade production architecture for the MarketAI application, satisfying strict requirements for scalability, cost-control, security, and distributed observability.

## 1. Final Required Stack & Containerization (`docker-compose.yml`)
The monolithic Next.js application has been logically decoupled into discrete scaling planes matching the exact required stack:
- **Next.js** (`web`): Frontend rendering, UI, and Server-Sent Event clients.
- **FastAPI** (`api`): Highly concurrent Python API backend serving `/api/v1/research`.
- **PostgreSQL**: Primary durable database.
- **Redis**: In-memory data store for Distributed rate limiting, Celery Job broker, and caching.
- **Celery**: Distributed task queue workers mapping complex research stages.
- **Object Storage** (`minio`): S3-compatible blob storage for raw evidence scraping and final PDF artifacts.

## 2. Worker Fleet & Multiple Queues
Instead of processing all workloads on a single thread pool, the architecture splits Celery workloads into distinct queues:
- **`research.quick` / `research.deep`**: Handled by `worker-research` instances interacting with LLM providers.
- **`analysis`**: Handled by `worker-analysis` running deterministic financial engines.
- **`reports`**: Handled by `worker-pdf` interacting exclusively with the S3 object store.
This ensures low-priority or heavy IO operations do not starve enterprise API traffic.

## 3. Database Schema (PostgreSQL)
Replaced the NoSQL / local SQLite dependencies with a strict relational model defined in `backend/models.py`:
- `users`, `organizations`, `organization_members` (Tenant isolation and Auth)
- `research_jobs` (State machine tracking: QUEUED -> RESEARCHING -> ANALYZING -> COMPLETED)
- `evidence`, `claims` (Source verification, content hashing, authority scoring)
- `usage_events` (Per-tenant accounting, billing, and LLM token constraints)

## 4. Multi-Layer Security & Protection
- **Idempotency**: API endpoints expect `idempotencyKey` values. The FastAPI backend hashes and verifies these against the database before initiating Celery workers to prevent duplicate billing.
- **SSRF & Prompt Sanitization**: Integrated network security checking to isolate user-provided parameters before they hit the Celery pipeline.

## 5. Background PDF Pipeline
PDF generation is strictly asynchronous:
1. `worker-analysis` completes the data processing and submits job ID to `reports` queue.
2. `worker-pdf` renders the document and uses `boto3` to push the artifact to S3 (MinIO).
3. The database updates the `pdf_object_key`, allowing the API to vend secure URLs.
