# MarketAI — Intelligence on Demand

MarketAI is an enterprise-grade, AI-powered market research platform. It generates comprehensive, top-tier market research, competitor analysis, and launch briefs in under a minute by integrating real-time web search and advanced Large Language Models (LLMs). 

## 🏗 System Architecture

The application is built on a highly scalable, distributed microservices architecture designed to handle concurrent research jobs with high reliability and performance.

```text
                                  CDN / WAF
                                      │
                                Load Balancer
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
               Next.js × N                         FastAPI × N
               (Frontend)                           (Backend API)
                                                        │
                         ┌──────────────────────────────┼──────────────────────────────┐
                         │                              │                              │
                    PostgreSQL                       Redis                       Object Storage
               (Durable Persistence)        (Cache & Queue Broker)              (S3 / MinIO)
                         │                              │                              │
                         │                         Job Queues                          │
                         │                              │                              │
                         │           ┌──────────────────┼──────────────────┐           │
                         │           │                  │                  │           │
                         │       Research           Analysis              PDF          │
                         │        Workers            Workers            Workers        │
```

## 🚀 Key Features

*   **Deep Research Engine**: Utilizes Google Search grounding and elite AI prompting (consultant-grade) to synthesize executive summaries, unit economics, SWOT analyses, and go-to-market strategies.
*   **Durable Persistence**: Fully relational PostgreSQL database managing `users`, `organizations`, `research_jobs`, `subscriptions`, and `audit_events`.
*   **Asynchronous Job Processing**: Celery distributed task queues backed by Redis to manage long-running Research, Analysis, and PDF generation workers asynchronously.
*   **Enterprise Security & Auth**: Multi-layered security including JWT/Session handling, Role-Based Access Control (RBAC), tenant isolation, API versioning (`/v1/...`), and strict CORS/rate limiting.
*   **Scalable Object Storage**: S3-compatible blob storage (e.g., AWS S3, MinIO) for storing immutable PDF reports, large evidence documents, and raw snapshots.
*   **Top-Tier UX**: Custom Next.js 15+ App Router frontend featuring high-fidelity sweeping progress animations, robust React error boundaries, and a custom native Markdown renderer optimized for financial and strategic reporting.
*   **Metering & Quota Engine**: Built-in subscription and entitlement layer to manage user/organization plan limits, LLM token tracking, API usage, and daily/monthly quotas.

## 🛠 Tech Stack

**Frontend (Client/UI)**
*   Framework: [Next.js 15+ (App Router)](https://nextjs.org/)
*   Language: TypeScript
*   Styling: Tailwind CSS
*   Markdown Rendering: Custom inline regex parser for fast, dependency-free text generation
*   UI Animations: Custom CSS (`animate-sweep`) & Framer Motion (where applicable)

**Backend (API/Workers)**
*   API Framework: [FastAPI](https://fastapi.tiangolo.com/) (Python)
*   Task Queue: [Celery](https://docs.celeryq.dev/)
*   Database ORM: SQLAlchemy / SQLModel

**Infrastructure & Services**
*   Relational DB: PostgreSQL
*   Cache/Broker: Redis (Managed Redis recommended for production)
*   Object Storage: AWS S3 / MinIO
*   AI Model: Google Gemini API (via `@google/genai`)

## 💻 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (3.10+)
*   PostgreSQL
*   Redis Server

### Installation

1. **Clone the repository and install frontend dependencies:**
   ```bash
   npm install
   ```

2. **Setup environment variables:**
   Copy the example environment files and add your secrets (Gemini API keys, Database URLs, Redis URLs, S3 access keys).
   ```bash
   cp .env.example .env.local
   ```

3. **Start the Frontend Development Server:**
   ```bash
   npm run dev
   ```
   Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

4. **Start the Backend API & Workers:**
   *Navigate to the `/backend` directory (if structured internally)*
   ```bash
   uvicorn main:app --reload
   celery -A tasks worker --loglevel=info
   ```

## 🛡 API Versioning & Security

All external integrations and internal UI calls route through the versioned API:
*   `/v1/research`
*   `/v1/research/{id}/events`
*   `/v1/usage`
*   `/v1/billing`

Every request implements token-based authentication, strict body-size limits, execution timeouts, and rate limits managed globally via Redis distributed locks.

## 🤝 Contributing
For bug reports and feature requests, please open an issue on the repository. Adhere to the code quality guidelines established in the respective frontend and backend toolchains.
