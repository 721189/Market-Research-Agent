# MarketAI — Autonomous Market Intelligence & Strategic Analysis

**MarketAI** is an AI-powered market intelligence platform designed for founders, product managers, corporate strategists, and venture investors. It transforms raw product ideas, market questions, or competitor names into structured, consultant-grade market research briefs in seconds.

---

## 🎯 What MarketAI Does

Building a comprehensive market research memo typically requires 20–40 hours of manual desk research: scanning competitor offerings, estimating market sizing (TAM/SAM/SOM), compiling customer sentiment, analyzing unit economics, and formatting go-to-market strategies.

MarketAI automates this discovery lifecycle by combining real-time web search grounding with frontier LLMs and structured analytical workflows:

- **Instant Market Sizing & Validation**: Quantitative TAM/SAM/SOM breakdowns, target ICP definitions, customer pain maps, and willingness-to-pay signals.
- **Deep Competitor Intelligence**: Direct competitor matrices, feature gap analyses, pricing models, strategic moats, and defensive vulnerabilities.
- **Unit Economics & Financial Projections**: Estimated CAC, LTV:CAC ratios, payback periods, gross margin benchmarks, and monetization roadmaps.
- **Actionable Go-To-Market Plans**: Phased launch checklists (30/60/90 days), high-converting acquisition channels, positioning taglines, and regulatory risk mitigation.
- **Live Visual Analytics & Export**: Dynamic interactive charts, real-time stage progress monitoring, and downloadable executive PDF memos.

---

## 💡 Real-World Use Cases

| Persona | Workflow | Outcome |
| :--- | :--- | :--- |
| **Startup Founders** | Validate idea viability before writing code | Instant investor-ready brief with positioning, risk factors, and competitor teardowns |
| **Product Managers** | Benchmark new feature concepts vs. industry | Feature-by-feature matrix, pricing tier comparisons, and customer friction points |
| **Strategy & Ops** | Fast market sizing for corporate initiatives | Defensible TAM/SAM models, macro trends, and threat landscape overviews |
| **VCs & Angels** | Rapid diligence on deal flow & pitches | Unbiased third-party assessment of claim veracity, market saturation, and defensibility |

---

## 🔍 Honest Capabilities & Limitations

We believe in radical transparency about what AI-driven market intelligence can and cannot do:

### ✅ What MarketAI Does Exceptionally Well
- **Speed & Breadth**: Scans broad market segments and synthesizes hundreds of public data points into coherent executive frameworks within 30–60 seconds.
- **Structural Rigor**: Uses battle-tested consulting frameworks (SWOT, Porter's Five Forces, Jobs-To-Be-Done, Unit Economics) to avoid unstructured chatter.
- **Fast Hypothesis Testing**: Allows operators to iterate through 10 variations of a product angle in an afternoon.
- **Multi-Tenant Security & Isolation**: Strict data segregation per organization with complete encryption at rest and in transit.

### ⚠️ Known Limitations & Operator Considerations
- **Private Data Blindspots**: MarketAI relies on public web data and generative reasoning. It cannot access proprietary internal databases, private company cap tables, or NDA-protected financials.
- **Estimates vs. Audited Numbers**: Unit economics and market sizes are model projections grounded in publicly reported benchmarks; they should serve as directional baselines rather than audited accounting.
- **Search Latency & Model Quotas**: Deep multi-agent synthesis involves heavy grounding calls and token generation. Under high load or strict external API rate limits, jobs may queue for processing.
- **Dynamic Markets**: For rapidly evolving niche regulations or breaking news from the past 24 hours, supplementary human verification is always recommended.

---

## 🏗 Architecture & Infrastructure

MarketAI is engineered as a robust, microservices-based full-stack platform:

```
                            [ Web Traffic / Users ]
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │  Cloud Run / Nginx Ingress   │
                       └──────────────┬───────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ┌─────────────────────┐                         ┌─────────────────────┐
   │ Next.js 15+ UI/Web  │                         │  FastAPI Backend    │
   │  - App Router       │                         │  - REST API / Auth  │
   │  - Recharts / D3    │                         │  - Rate Limiting    │
   │  - SSE / Polling    │                         │  - Stripe Billing   │
   └─────────────────────┘                         └──────────┬──────────┘
                                                              │
                                     ┌────────────────────────┴────────────────────────┐
                                     ▼                                                 ▼
                          ┌─────────────────────┐                           ┌─────────────────────┐
                          │ PostgreSQL (Data)   │                           │ Redis (Queue/Cache) │
                          │  - Tenants & Orgs   │                           │  - Distributed Lock │
                          │  - Research Memos   │                           │  - Rate Windows     │
                          │  - Audit Logs       │                           └──────────┬──────────┘
                          └─────────────────────┘                                      │
                                                                                       ▼
                                                                            ┌─────────────────────┐
                                                                            │ Celery Worker Pool  │
                                                                            │  - Research Engine  │
                                                                            │  - Analysis Engine  │
                                                                            │  - PDF Generator    │
                                                                            └──────────┬──────────┘
                                                                                       │
                                                                                       ▼
                                                                            ┌─────────────────────┐
                                                                            │ Object Storage (S3) │
                                                                            │  - Generated PDFs   │
                                                                            │  - Report Artifacts │
                                                                            └─────────────────────┘
```

---

## 📦 Tech Stack

- **Frontend**: Next.js 15+ (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons, Recharts.
- **Backend API**: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy ORM.
- **Async Workers**: Celery distributed task queue backed by Redis with worker auto-scaling.
- **Database & Storage**: PostgreSQL 15, Redis 7, S3 / MinIO compatible object storage.
- **AI Core**: Google Gemini Flash & Pro models via `@google/genai` with search grounding.
- **Billing & Subscriptions**: Stripe Checkout, Billing Portal, and idempotent webhook lifecycle management.
- **Telemetry & Observability**: Prometheus metrics (`/metrics`), W3C distributed tracing (`traceparent`), structured JSON logs, and real-time alert engine (`/alerts`).

---

## 🚦 Quick Start Guide

### 1. Prerequisites
- **Node.js**: v18.x or higher
- **Python**: v3.10 or higher
- **PostgreSQL**: v14+
- **Redis**: v6+
- **Gemini API Key**: From [Google AI Studio](https://aistudio.google.com/)

### 2. Environment Configuration
Copy the `.env.example` file and populate your credentials:

```bash
cp .env.example .env.local
```

Essential variables:
```env
# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Persistence & Caches
DATABASE_URL=postgresql://marketai:password@localhost:5432/marketai
REDIS_URL=redis://localhost:6379/0

# Storage & Security
SECRET_KEY=your_secure_32_character_jwt_secret
S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin_secure_pw

# Optional: Billing (Stripe)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 3. Run with Docker Compose (Recommended for Local Full-Stack)
Launch the entire system (Frontend, API, Workers, Postgres, Redis, MinIO) in one command:

```bash
docker-compose up --build
```

Access services:
- **Web Application**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Health Check**: `http://localhost:8000/api/v1/health`

### 4. Run Manually for Local Development

#### Frontend:
```bash
npm install
npm run dev
```

#### Backend API:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

#### Background Worker:
```bash
celery -A backend.app.workers.celery_app worker -Q research.quick,research.deep,analysis,reports --loglevel=info
```

---

## 🛡 Security, Compliance & Multi-Tenancy

- **Row-Level Organization Isolation**: All database queries enforce strict tenant scoping (`org_id`).
- **Input Sanitization & Guardrails**: Defense against SSRF, prompt injections, and untrusted payload execution.
- **Least Privilege Access**: Role-based permissions (`Owner`, `Admin`, `Member`, `Viewer`) gating billing, job deletion, and user invitations.
- **Fail-Open Rate Limiting**: Token-bucket and sliding-window rate limiting designed with in-memory degradation if Redis experiences transient partitions.
- **Disaster Recovery**: Built-in verification script (`scripts/disaster_recovery_drill.py`) verifying RTO (<15 min) and RPO (<5 min) operational readiness.

---

## 📄 License & Commercial Usage

MarketAI is enterprise-ready software. All rights reserved. For commercial enterprise licensing, custom LLM fine-tuning, or on-prem air-gapped deployments, contact our enterprise solutions team.
