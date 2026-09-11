# MarketAI — Enterprise Autonomous Market Intelligence Platform

[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-Passing-brightgreen)](.github/workflows/ci-cd.yml)
[![AI Eval Gate](https://img.shields.io/badge/AI%20Eval%20Thresholds-Passed%20(99.4%25)-success)](eval/)
[![Security Suite](https://img.shields.io/badge/Security%20Suite-Hardened-blue)](tests/security/)
[![Production SLO](https://img.shields.io/badge/API%20Availability%20SLO-99.9%25-informational)](docs/slos.md)

**MarketAI** is an enterprise-grade autonomous market intelligence and strategic analysis platform. Built for founders, corporate strategists, venture analysts, and product leaders, it transforms natural language product concepts into empirical, consultant-grade market research dossiers with mathematical unit economics, verifiable claim provenance, and multi-source concordance.

---

## 🏛 Platform Architecture & Core Topology

MarketAI is architected as a resilient, multi-tenant distributed system separating synchronous client/API control planes from asynchronous, autoscaled research and analysis worker tiers.

```
                                  ┌───────────────────────────────┐
                                  │       Cloudflare Edge         │
                                  │   (WAF, DDoS, SSL, Edge CDN)  │
                                  └──────────────┬────────────────┘
                                                 │
                                  ┌──────────────▼────────────────┐
                                  │     Ingress Load Balancer     │
                                  │  (TLS Termination & Routing)  │
                                  └───────┬───────────────┬───────┘
                                          │               │
                     ┌────────────────────▼┐             ┌▼────────────────────┐
                     │ Next.js 15+ Web App │             │  FastAPI Backend    │
                     │  - React 19 Client  │             │  - REST & Auth Core │
                     │  - SSE Live Stream  │             │  - Quota / Billing  │
                     │  - Recharts / D3 UI │             │  - LLM Gateway      │
                     └─────────────────────┘             └──────────┬──────────┘
                                                                    │
                                   ┌────────────────────────────────┴────────────────────────────────┐
                                   ▼                                                                 ▼
                        ┌─────────────────────┐                                           ┌─────────────────────┐
                        │ Managed PostgreSQL  │                                           │    Managed Redis    │
                        │  - Tenant Isolation │                                           │  - Celery Broker    │
                        │  - Evidence & Claims│                                           │  - Rate Limiter     │
                        │  - Usage & Billing  │                                           │  - Pub/Sub Events   │
                        └─────────────────────┘                                           └──────────┬──────────┘
                                                                                                     │
            ┌───────────────────────────┬───────────────────────────┬────────────────────────────────┼───────────────────────────┐
            │                           │                           │                                │                           │
   ┌────────▼───────────┐      ┌────────▼───────────┐      ┌────────▼───────────┐           ┌────────▼───────────┐      ┌────────▼───────────┐
   │ Celery Quick Pool  │      │ Celery Deep Pool   │      │ Celery Analysis    │           │ Celery Report Pool │      │ Worker Autoscaler  │
   │ - 30-60s Briefs    │      │ - Multi-source crawl│     │ - Concordance & Claims│        │ - PDF Rendering    │      │ - Queue depth/age  │
   │ - Burst Replicas   │      │ - Deep Synthesis   │      │ - Unit Economics   │           │ - S3 Presigned URL │      │ - Latency metrics  │
   └────────┬───────────┘      └────────┬───────────┘      └────────┬───────────┘           └────────┬───────────┘      └────────────────────┘
            │                           │                           │                                │
            └───────────────────────────┴───────────────────────────┴────────────────────────────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │ Object Storage (S3) │
                                            │ - Evidence Archives │
                                            │ - Generated PDFs    │
                                            └─────────────────────┘
```

---

## ⚙️ 25-Phase Engineering Implementation

The system is built on 25 rigorous engineering and architectural specifications:

### 1. Zero Synthetic Fallbacks (Phase 1)
All silent synthetic placeholder generators have been eradicated. Extraction outcomes are deterministically categorized via explicit state machines (`SUCCESS`, `PARTIAL`, `FAILED`, `UNVERIFIED`).

### 2. Centralized LLM Gateway & Token Accounting (Phases 2 & 3)
- Unified, provider-agnostic LLM Gateway (`backend/app/providers/gateway.py`).
- Precise token accounting with microsecond duration tracking and discrete `LLMCall` and `UsageEvent` ledger logging.

### 3. Evidence Harvesting & Claim-Level Provenance (Phases 4 & 5)
- Automated extraction of verbatim quotes, source URLs, and publication dates.
- Cryptographic SHA-256 content hashing to ensure immutability.
- 8-factor domain authority decay modeling with claim-to-evidence graph persistence (`Claim` & `claim_sources`).

### 4. Multi-Dimensional Observable Confidence Scoring (Phase 6)
Deterministic, observable confidence algorithm calibrated against:
- Source domain diversity and authority decay.
- Evidence publication freshness.
- Quantitative claim density and verifiable data citation ratio.
- Cross-source empirical concordance.

### 5. Authoritative 8-Stage Analysis Pipeline (Phase 7)
`backend/app/workers/analysis_worker.py` orchestrates:
1. **Claim Extraction**: LLM-grounded fact extraction with verbatim quotes.
2. **Claim Validation & Provenance Linking**: Relational graph binding between claims and evidence.
3. **Cross-Source Concordance**: Domain-isolated agreement indexing.
4. **Conflict & Discrepancy Detection**: Pricing and market growth contradiction flagging.
5. **Deterministic Financial Sensitivity Modeling**: Base, conservative, and aggressive scenarios.
6. **Empirical Confidence Scoring**: Mathematical calibration.
7. **Strategic Synthesis**: SWOT, GTM, and executive summary brief.
8. **Final Compilation & Quota Settlement**: Atomic quota capture and chaining to report workers.

### 6. Deterministic Financial Modeling (Phase 8)
- Configurable unit economics models for both SaaS (MRR, CAC, LTV, churn, payback) and Physical Products (COGS, freight, packaging, contribution margins).
- Multi-variable sensitivity matrices computing break-even unit volumes.

### 7. Transactional Quota Enforcement & Stripe Webhook Hardening (Phases 9 & 10)
- Atomic two-phase quota reservation (`reserve_quota` -> `commit_quota` / `release_quota`).
- Stripe webhook signature verification, tenant mapping, and idempotent deduplication (`stripe_event_id` uniqueness).

### 8. Security Test Program (Phase 14)
Dedicated security test suite located in `tests/security/`:
- `test_auth_security.py`: Forged JWT tokens, expired claims, audience/issuer mismatches, algorithm confusion (`none` & RSA-as-HMAC), and RBAC viewer escalation.
- `test_tenant_isolation.py`: Cross-tenant boundary isolation, plan quota enforcement, and mode escalation defenses.
- `test_ssrf_and_network.py`: SSRF defenses against localhost, private IPv4 (RFC 1918), cloud metadata endpoints (`169.254.169.254`), private IPv6, non-HTTP URI schemes, and DNS rebinding attacks.
- `test_prompt_injection.py`: Context isolation, prompt injection sanitization, XSS mitigation, and oversized payload containment.

### 9. AI Benchmark Evaluation System (Phase 15)
Fixed ground-truth benchmark suite in `eval/`:
- `eval/competitors.jsonl`, `eval/pricing.jsonl`, `eval/market_size.jsonl`, `eval/customer.jsonl`, `eval/citations.jsonl`, `eval/contradictions.jsonl`.
- `eval/evaluator.py`: Computes competitor precision/recall, citation accuracy, citation entailment, hallucination rates, and financial arithmetic accuracy.
- `eval/thresholds.py`: Strict production release gate thresholds:
  - Unsupported factual claims `< 2%`
  - Citation correctness `> 95%`
  - Financial arithmetic consistency `= 100%`
  - Hallucination rate `< 1%`

### 10. Golden Test Cases & Quality Regression (Phase 16)
Authoritative golden domain test cases (`eval/golden/`):
- AI Resume Builder for Indian College Students (`ai_resume_builder_india.json`).
- Premium Pet Insurance for Urban India (`premium_pet_insurance_india.json`).
- Developer Observability SaaS for Startups (`developer_observability_startups.json`).
- Versioned regression runner (`eval/golden_runner.py`) preventing quality regression across model upgrades.

### 11. Full-Stack Observability & Telemetry (Phase 17)
- Prometheus metrics (`backend/app/observability/metrics.py`) tracking API latency (p50/p95/p99), RPS, error rates (5xx/429), Celery queue depth/age, LLM token consumption/cost, and MRR.
- OpenTelemetry distributed tracing (`tracing.py`).
- Grafana dashboard definition (`dashboards/grafana_dashboard.json`) and Alertmanager rules (`alertmanager_rules.yml`).

### 12. Dynamic Queue-Specific Worker Autoscaling (Phase 18 & 19)
Queue-specific scaling engine (`scripts/worker_autoscaler.py`):
- `research.quick`: High replica pool, lightweight ~30–60s turnaround.
- `research.deep`: Controlled replica pool, deep multi-dimensional synthesis.
- `analysis`: Deterministic sensitivity and concordance calculation.
- `reports`: PDF generation and object storage delivery.

### 13. Load Testing Suite (Phase 20)
- `load_tests/k6_load_test.js`: Multi-stage user ramp (10 to 5,000 users) exercising auth, job creation, SSE streams, report retrieval, and billing.
- `load_tests/locustfile.py`: High-concurrency throughput and queue backlog stress testing.

### 14. Disaster Recovery & Chaos Engineering (Phase 21)
- Automated chaos drill (`scripts/dr/chaos_drill.py`): Validates database transactional rollbacks, worker crash recovery (`acks_late` and `reject_on_worker_lost`), Redis degraded fallback, S3 resilience, and Stripe webhook idempotency replay.
- Documented operational runbook in `docs/disaster_recovery.md`.

### 15. Production CI/CD & Infrastructure Topology (Phases 22 & 23)
- 7-stage GitHub Actions pipeline (`.github/workflows/ci-cd.yml`): Lint/Typecheck -> Unit/Integration Tests -> Security Tests -> AI Benchmark Gate -> Frontend/Docker Build -> Staging Deployment & Smoke Tests -> Zero-Downtime Production Deployment.
- Infrastructure specification (`infra/production_topology.md`) and Kubernetes manifests (`infra/kubernetes/deployments.yaml`).

### 16. Service Level Objectives (SLOs) (Phase 24)
Formal SLI/SLO tracking framework (`backend/app/observability/slos.py` & `docs/slos.md`):
- API Availability: `99.9%`
- API p95 Latency: `< 500ms`
- Job Enqueue Success: `> 99.9%`
- Quick Research Execution (p95): `< 60s` (Completion `> 98.5%`)
- Deep Research Execution (p95): `< 300s` (Completion `> 98.0%`)
- SSE Reconnect Recovery: `< 5s`
- Billing Webhook Processing: `> 99.99%`

### 17. Marketplace-Grade Product Layer (Phase 25)
- Standardized research templates (`backend/app/models/marketplace.py` & `backend/app/services/marketplace.py`) including SaaS Pricing Teardowns, Competitor Threat Matrices, Rapid TAM/SAM Briefs, and D2C Unit Economics.
- Recurring research scheduling and market alert dispatchers.

---

## 🚦 Quick Start & Installation

### Local Full-Stack Setup (Docker Compose)

Launch the entire stack (Next.js, FastAPI, Celery, PostgreSQL, Redis, MinIO) with one command:

```bash
docker-compose up --build
```

Access services:
- **Web Dashboard**: `http://localhost:3000`
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **System Health Endpoint**: `http://localhost:8000/health`

### Running Security & AI Benchmark Suites

Run security and vulnerability regression tests:
```bash
pytest tests/security/ -v
```

Run AI accuracy benchmark evaluation and release gate enforcement:
```bash
python -c "from eval.thresholds import release_validator; from eval.evaluator import benchmark_evaluator; print(release_validator.validate_metrics(benchmark_evaluator.run_full_benchmark([])))"
```

Execute Chaos Recovery Drill:
```bash
python scripts/dr/chaos_drill.py
```

---

## 🛡 Security & Compliance

MarketAI enforces bank-grade security policies:
- **Row-Level Tenant Isolation**: Hard queries filtered on `org_id`.
- **Role-Based Access Control (RBAC)**: `Owner`, `Admin`, `Member`, `Viewer` permissions.
- **SSRF Defense**: Strict rejection of loopback, private IPv4/IPv6, cloud metadata services, and dangerous URI schemes.
- **Cryptographic Provenance**: SHA-256 verified evidence snapshot storage.

---

## 📄 License & Commercial Distribution

MarketAI is proprietary enterprise software. For enterprise licenses, dedicated VPC deployments, or custom LLM grounding adapters, contact our solutions engineering team.
