# MarketAI Production Architecture

This document describes the enterprise-grade production architecture for the MarketAI application, satisfying strict requirements for scalability, cost-control, security, and distributed observability.

## 1. Containerization & Topology (`docker-compose.yml`)
The monolithic Next.js application has been logically decoupled into discrete scaling planes:
- **`web`**: Next.js frontend rendering, CDN caching.
- **`api`**: Dedicated Next.js API server handling `v1/*` routes, auth validation, and quota pre-checks.
- **`worker-research`**: Dedicated queue workers for executing Gemini API calls and search extraction.
- **`worker-report`**: Background worker for generating heavy PDF blobs asynchronously.

## 2. Infrastructure as Code (Terraform)
While this workspace is serverless, the equivalent Terraform modules (`main.tf`) deploy:
- **GCP Cloud Run / AWS ECS**: Auto-scaling container fleets for `web`, `api`, and `workers`.
- **Cloud SQL (PostgreSQL)**: Scalable relational datastore (connection pooling via PgBouncer).
- **Redis (Memorystore/ElastiCache)**: Used for distributed rate limiting, job locks, and caching duplicate research hashes.
- **Object Storage (S3 / GCS)**: Secure, versioned bucket for PDF artifacts.

## 3. Cost-Control & Quota Engine
- **Pre-flight Quota Checks**: `app/lib/research/billing.ts` enforces limits across `free`, `pro`, and `enterprise` tiers before any external API is hit.
- **Deduplication Engine**: `engine.ts` calculates a SHA-256 hash of normalized user queries. If a query was completed successfully in the last 7 days, it returns the cached report, saving up to 100% of LLM and Search costs.
- **Usage Metering**: Tracks total tokens, execution time (ms), models used, and estimated USD spend per execution in the `usage` collection.

## 4. Multi-Layer Security & Protection
- **API Versioning**: All endpoints migrated cleanly to `/api/v1/research`.
- **SSRF Protection**: `app/lib/research/security.ts` blocks local IP resolutions (`127.0.0.1`, `10.x.x.x`), DNS rebinding, and validates protocols.
- **Prompt Sanitization**: Untrusted inputs are aggressively scrubbed to prevent system-prompt poisoning.
- **Rate Limiting**: Designed to utilize a multi-key strategy combining IP, `userId`, and `orgId` across Redis sliding windows.

## 5. Background PDF Pipeline
PDF generation has been stripped out of the synchronous GET request path:
1. `executeResearchJob` finishes and saves the structured payload.
2. `queuePdfGeneration` fires asynchronously to the background worker.
3. The background worker renders the PDF and saves the Base64 Blob (simulating Object Storage).
4. The client polls the `/pdf` endpoint and receives a 202 until the PDF is `READY`, at which point it is downloaded securely.

## 6. CI/CD & Evaluation
- **Automated Testing**: Pull Requests trigger formatting, linting, and type checking (`npm run lint`, `tsc`).
- **AI Evals**: The evaluation pipeline validates pricing hallucinations and formatting regressions using a golden dataset.
- **Metrics/Tracing**: Standardizing around OpenTelemetry for request latency, LLM failures, and worker queue depths.
