# CrewAI AMP Deployment (deploy/)

This directory is a self-contained **CrewAI AMP Flow** project built from the
market-research-agent codebase so it can be deployed to CrewAI AMP.

## Local validation & deploy

From inside this `deploy/` directory:

```bash
# 1. Install the CrewAI CLI (already installed in the repo's venv)
pip install crewai

# 2. Authenticate with CrewAI AMP (interactive — requires your account)
crewai login

# 3. Ensure dependencies are locked and the entrypoints resolve
uv lock
uv sync

# 4. Validate the project against AMP's deploy rules (does not require login)
crewai deploy validate

# 5. Create and push the deployment
crewai deploy create
crewai deploy push
```

`kickoff` runs the flow headlessly and prints the JSON result:

```bash
PRODUCT_IDEA="Smart Water Bottle" ANALYSIS_MODE=deep uv run market-research-agent
```

## Notes

- `pyproject.toml` declares `[tool.crewai] type = "flow"` and the
  `kickoff` / `run_with_trigger` console scripts.
- `src/market_research_agent/main.py` defines the `MarketResearchAgentFlow`
  subclass (required by AMP validation) which calls the same headless
  pipeline as the repository root (`flow.auto_research_async`).
- The supporting modules (`state`, `agents`, `tasks`, `tools`, `routing`,
  `schemas`, `hitl`, plus the security helpers `pii_redactor`, `audit`,
  `logging_config`) are copied here as a deployable **snapshot** with
  package-relative imports. If you change the root modules, re-sync them here
  before redeploying.
- `crewai login` and `crewai deploy push` require your CrewAI AMP account and
  can only be run interactively on a machine with your credentials.