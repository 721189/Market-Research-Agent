
🧠  Multi-Agent Market Intelligence Engine


> An asynchronous, stateful CrewAI orchestration engine that automates market research, competitor pricing, and unit-economics modeling—**now with Human-in-the-Loop review, PDF reporting, semantic caching, and Docker support**.


## 🎯 The Core Idea

**The Problem:** Founders and product managers spend weeks manually scraping competitor data. Consultants charge $5,000–$10,000 for a single report.

**The Solution:** This project codifies that consulting workflow into a **stateful, event-driven CrewAI Flow** with:
1. Web scraping (Tavily)
2. Financial analysis (Pydantic-validated)
3. **Human-in-the-Loop review** (approve/reject financials before the brief is generated)
4. Confidence scoring on every insight
5. Professional PDF report generation
6. **Semantic caching** (SQLite) to save 30-50% on API costs


✨ Key Features (Updated Aug 10, 2026)

| Feature | Description |
| :--- | :--- |
| **Stateful CrewAI Flows** | Event-driven workflow with branching (`@start`, `@listen`) instead of sequential scripts. |
| **Human-in-the-Loop (HITL)** | Custom review gate pauses execution at the financial analysis stage. Humans approve or edit numbers before the launch brief is generated. Prevents hallucinated costs (e.g., $0.12 coffee cup). |
| **Confidence Scoring** | Each insight is scored out of 100 based on source reliability, evidence coverage, consistency, and LLM self-assessment. |
| **PDF Export (reportlab)** | One-click generation of McKinsey-style consulting reports with financial tables, executive summaries, and confidence scores. |
| **Semantic Caching (SQLite)** | Stores query+response pairs. Repeated queries return instantly—saves tokens and money. |
| **Dockerized** | Fully containerized with `Dockerfile` and `docker-compose.yml` for one-command deployment. |
| **Streamlit Dashboard** | Interactive UI with real-time progress tracking, A/B testing, and download buttons. |

---

## 🏗️ Architecture & Workflow (Current v2.0)

```mermaid
flowchart TD
    User[User Input: Product Idea] --> UI[Streamlit Dashboard]
    UI --> Flow[CrewAI Flow Orchestrator]
    
    subgraph Flow [Stateful Event-Driven Pipeline]
        direction TB
        P1[Phase 1: Scrape + Financials] --> P2[Human-in-the-Loop Review Gate]
        P2 -->|Approved| P3[Phase 2: Launch Brief + Confidence]
        P2 -->|Rejected| P1
    end
    
    Flow --> Cache[Semantic Cache (SQLite)]
    Cache -->|Cache Hit| UI
    Cache -->|Cache Miss| Agents
    
    subgraph Agents [Agentic Crew]
        Scraper[Trend Scraper] --> Analyst[Financial Analyst]
        Analyst --> Director[Product Director]
    end
    
    Agents --> PDF[PDF Export (reportlab)]
    PDF --> UI
```

**What Makes This Different:**
- **Phase 1:** Trend Scraper + Financial Analyst run. Output is validated via Pydantic.
- **HITL Gate:** Streamlit pauses and shows the financial numbers to the user. User approves, edits, or rejects.
- **Phase 2:** Only after approval, the Product Director generates the launch brief and Confidence Score.
- **Semantic Cache:** Checks if an identical product was researched before. If yes, returns instantly.

---

## 📸 Live Demo

<img width="1266" height="673" alt="Screenshot 2026-08-07 183247" src="https://github.com/user-attachments/assets/8ddfda83-d619-430d-a026-e6a8ae018555" />

<img width="1218" height="662" alt="Screenshot 2026-08-07 183409" src="https://github.com/user-attachments/assets/abadaadb-9071-421d-a9e0-54688503ab31" />

---

## 💡 Why This Project?

**The Honest Truth:** This doesn't replace a consulting firm—it replaces the *discovery phase*. It gives you a 70% complete, *human-verified* foundation in 60 seconds.

**Engineering Motivation:**
- **Agentic Design Patterns:** Event-driven Flows with conditional branching.
- **Cost-Efficient AI:** Groq Llama 3.3 70B for deep analysis, caching to avoid repeat costs.
- **Responsible AI:** HITL review gates prevent hallucinations from reaching the final report.

---

## 🎯 Who Is This For?

| Role | Value |
| :--- | :--- |
| **Solopreneurs / Founders** | Validate product viability without paying $10k. |
| **Product Managers** | Benchmark competitors in minutes, not weeks. |
| **AI Engineers** | Study CrewAI Flows, HITL, and caching patterns. |
| **Hackathon Teams** | Generate business plans to pitch alongside prototypes. |

---

## ⚠️ Honest Limitations (v2.0)

1. **COGS still requires human validation:** The Confidence Score will flag low-confidence numbers (like $0.12 COGS), but you must use the HITL gate to correct it.
2. **Freshness Reliance:** Quality depends on Tavily search results. If the web has no data on your niche, the agents extrapolate from adjacent markets.
3. **Latency:** The full pipeline (including HITL) takes ~60 seconds per query. Cached queries return instantly.

---

## 📦 Requirements

- **Python 3.9+**
- **API Keys Required:**
  - [Groq API Key](https://console.groq.com/)
  - [Tavily API Key](https://tavily.com/)

---

## 🚀 Quick Start (Local Setup)

**1. Clone the Repository**
```bash
git clone https://github.com/721189/Market-Research-Agent.git
cd Market-Research-Agent
```

**2. Set up a Virtual Environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxx
```

**5. Run the Streamlit App**
```bash
streamlit run main.py

Enter a product idea (e.g., "Electric scooter"), review the financials when prompted, and download your PDF report.

**6. Run with Docker (Optional)**
```bash
docker-compose up --build




## 📁 Project Structure (v2.0)


Market-Research-Agent/
├── agents.py              # Agent definitions (Trend, Financial, Director)
├── tasks.py               # Task definitions with Pydantic schemas
├── tools.py               # Tavily web search tool wrapper
├── flow.py                # CrewAI Flow orchestrator (state machine)
├── hitl.py                # Custom Human-in-the-Loop provider for Streamlit
├── cache.py               # SQLite semantic caching layer
├── schemas.py             # Pydantic models (ConfidenceScore, FinancialAnalysis)
├── pdf_export.py          # reportlab PDF generator
├── main.py                # Streamlit UI entry point
├── tests/                 # Unit tests (pytest)
├── Dockerfile             # Container build instructions
├── docker-compose.yml     # Multi-service orchestration
├── requirements.txt       # Python dependencies
└── .env.example           # Template for environment variables
```

---

## 🛣️ Roadmap (What's Next)

✅ **Completed (v2.0):**
- [x] CrewAI Flows (event-driven)
- [x] Human-in-the-Loop review gate
- [x] Confidence Scoring
- [x] PDF Export (reportlab)
- [x] Semantic Caching (SQLite)
- [x] Dockerization

**Planned (v3.0):**
- [ ] **FastAPI Backend:** Replace Streamlit with a proper async API.
- [ ] **Celery + Redis:** For background task dispatch (non-blocking).
- [ ] **Batch Research:** Research multiple products in one go.
- [ ] **Collaborative Review:** Share HITL review links with team members.

---

## 🤝 Contributing

This is a self-contained prototype, but feel free to fork and experiment! If you build a "Manufacturing Estimator" agent or improve the COGS validation, I'd love to see it.


## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.



**Built with:** ❤️ by [Shivam Singh](https://github.com/721189) — Market research shouldn't cost $10,000.


**⭐ If this helped you, drop a star on GitHub! It helps other founders find it.**
