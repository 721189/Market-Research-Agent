# 🕵️ Market Research Agent

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-1.15-FF4D5D)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![TailwindCSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss)

**Multi-agent market research on autopilot.** Describe a product idea — a crew of
three AI agents scrapes your top competitors, models realistic unit economics,
pauses for **your review**, then delivers a confidence-scored go-to-market brief
with a stakeholder-ready PDF export.

## ✨ Features

- 🤖 **3-agent CrewAI pipeline** — Trend Scraper → Financial Analyst → Product Director
- ⏸️ **Human-in-the-loop review gate** — approve, edit, or reject the numbers before anything ships
- 🧮 **Structured unit economics** — COGS, retail price, gross margin (Pydantic-validated)
- 🎯 **Confidence scoring** — 0–100 trust score with per-dimension breakdown
- 📄 **PDF reports** — McKinsey-style one-click export
- ⚡ **Async by design** — FastAPI + Celery + Redis; the UI never blocks
- 🖥️ **Modern web dashboard** — Next.js 16 + Tailwind v4, animated pipeline stepper & confidence gauge
- 🔀 **Cost-aware LLM routing** — OpenRouter primary (free models) with automatic Groq fallback; slugs configurable via `.env`

## 🏗️ Architecture

```
┌────────────────┐   /api/* proxy   ┌────────────────────┐   enqueue   ┌───────────────────┐
│ Next.js UI     │ ───────────────► │ FastAPI :8000      │ ──────────► │ Celery worker     │
│ localhost:3000 │ ◄─────────────── │ POST /research     │ ◄────────── │ CrewAI pipeline   │
└────────────────┘    poll JSON     │ GET /research/{id} │   results   │ OpenRouter→Groq   │
                                    └────────────────────┘             └───────────────────┘
                                             ▲                                │
                                             │ PDF bytes                      ▼
                                    GET /research/{id}/pdf           Redis broker (:6379)
```

## 📁 Project structure

```
├── api/main.py            # FastAPI app: research endpoints + PDF export + CORS
├── frontend/              # Next.js 16 + Tailwind v4 web dashboard
│   └── app/               # landing page, /dashboard, lib/api.ts client
├── flow.py                # CrewAI Flow orchestration + HITL gate
├── agents.py              # agent factory + LLM construction
├── tasks.py               # task defs + FinancialAnalysis schema
├── routing.py             # cost-aware LLM routing (OpenRouter/Groq/DeepInfra)
├── hitl.py                # human-in-the-loop feedback provider
├── pdf_export.py          # reportlab PDF generation
├── worker/                # Celery app + research task
├── main.py                # legacy Streamlit UI (still functional)
└── tests/                 # pytest suite
```
## 🚀 Quickstart

### 0. Prerequisites
- Python 3.11+ with the project virtualenv at `venv/`
- Node.js LTS (for the frontend)
- A Redis server reachable on `localhost:6379` (options below)

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # then paste your keys
```

### 1. Redis — pick ONE

| Option | How |
|---|---|
| **Portable ZIP** (simplest) | [tporadowski/redis releases](https://github.com/tporadowski/redis/releases) → extract → `.\redis-server.exe` |
| **Memurai** | Windows-native Redis-compatible service; auto-starts on 6379 |
| **Docker** | `docker run -d --name mra-redis -p 6379:6379 redis:7-alpine` |
| **WSL** | `wsl` → `sudo apt install redis-server && sudo service redis-server start` |

> Windows has no official native `redis-server` binary — that's expected.

### 2. Celery worker

```powershell
.\venv\Scripts\python -m celery -A worker.research_task worker --loglevel=info --pool=solo
```

> ⚠️ **`--pool=solo` is required on Windows.** The default prefork pool crashes with
> `MemoryError` / `PermissionError [WinError 5]` under billiard's spawn model.

### 3. FastAPI

```powershell
.\venv\Scripts\python -m uvicorn api.main:app --reload
```

### 4. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000/dashboard**, describe a product idea, and launch.
The dev server proxies `/api/*` to FastAPI on `:8000` (no CORS setup needed).

> The legacy Streamlit UI still works too: `.\venv\Scripts\streamlit run main.py`

## 🔑 Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | yes* | Primary LLM provider ([get a key](https://openrouter.ai/keys)) |
| `TAVILY_API_KEY` | yes | Live web search for competitor scraping |
| `GROQ_API_KEY` | fallback | Used automatically when the OpenRouter key is missing |
| `DEEPINFRA_API_KEY` | no | Enables Batch API mode (~20% cheaper) |
| `OPENROUTER_SCRAPE_MODEL` | no | Override the cheap scrape model slug |
| `OPENROUTER_DEEP_MODEL` | no | Override the financial/brief model slug |

\* Runs fall back to Groq when OpenRouter is unconfigured.

### Free-tier survival guide

OpenRouter rotates its free models frequently and caps free usage:

- **404 "model not found"** → that free slug was retired. Browse live ones at
  [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0),
  then set `OPENROUTER_SCRAPE_MODEL` / `OPENROUTER_DEEP_MODEL` in `.env`.
- **429 "free-models-per-day"** → you hit the 50 requests/day cap. Each research
  run makes many LLM calls (tool loops), so expect ~2–5 runs/day. Adding
  **$10 credits raises the cap to 1000/day** and unlocks cheap paid models.

Current defaults (verified live): scrape = `nvidia/nemotron-3.5-lightning:free`,
deep = `nvidia/nemotron-3-super-120b-a12b:free`.

## 🔌 API reference

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/research` | `{"product_idea": "...", "mode": "quick\\|deep\\|batch"}` | `{"task_id": "..."}` |
| GET | `/research/{id}` | — | `{status, result?, error?}` — poll until `SUCCESS` |
| GET | `/research/{id}/pdf` | — | PDF report download (409 until complete) |

Interactive docs: <http://localhost:8000/docs>

## 🔄 The HITL flow

1. **Competitor Scrape** — Tavily-powered web research on the top 5 rivals
2. **Financial Margin** — structured COGS / retail / margin analysis
3. **⏸️ Review gate** — the pipeline pauses; approve, edit the numbers, or reject
4. **Launch Brief + Confidence** — final GTM brief scored 0–100 across source
   reliability, evidence coverage, and consistency

The headless API path auto-approves step 3 and hard-fails (triggering a Celery
retry) if phase two doesn't fully complete — no hollow reports.

## 🐳 Docker Compose

```bash
docker compose up --build   # redis + worker + api (+ legacy streamlit app)
```

## 🧪 Testing

```powershell
.\venv\Scripts\python -m pytest tests/ -q
```

## 🛠️ Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'crewai'` | You're using system Python — use `.\venv\Scripts\python -m ...` for every command |
| Celery `MemoryError` / `PermissionError [WinError 5]` | Add `--pool=solo` to the worker command (Windows requirement) |
| `Error 10061 connecting to localhost:6379` | Redis isn't running — start it (Quickstep step 1) |
| OpenRouter 404 on a `:free` model | Slug retired — pick a live one, override via `.env` (see above) |
| OpenRouter 429 daily limit | Wait for reset, or add $10 credits (cap becomes 1000/day) |
| Frontend proxy `ECONNREFUSED :8000` | FastAPI isn't running — start Terminal 3 |

## 📄 License

MIT — see [LICENSE](LICENSE).