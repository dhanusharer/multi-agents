# 🌾 Kisan Saathi (किसान साथी)

> **An ultra-unique, production-grade multi-agent AI system for Indian smallholder farmers.**

Built with **Google ADK** + **FastMCP** — designed for <2s latency, multilingual support (Hindi/English/Hinglish), and real-time integration with government data sources.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Farmer Query (Voice/Text)          │
└──────────────────────┬──────────────────────────┘
                       │
              ┌────────▼────────┐
              │   Orchestrator  │  gemini-2.5-flash
              │  (Intent Router)│  Few-shot prompting
              └───┬───┬───┬───┬┘
                  │   │   │   │
       ┌──────┐ ┌┴┐ ┌┴┐ ┌┴┐ ┌┴──────┐
       │ Crop │ │S│ │W│ │M│ │Security│
       │Advisor│ │c│ │e│ │a│ │ Guard  │
       │      │ │h│ │a│ │r│ │        │
       │      │ │e│ │t│ │k│ │        │
       │      │ │m│ │h│ │e│ │        │
       │      │ │e│ │e│ │t│ │        │
       └──┬───┘ └┬┘ └┬┘ └┬┘ └────────┘
          │      │   │   │
     ┌────▼──────▼───▼───▼────┐
     │    FastMCP Tool Server  │
     │   (kisan_mcp_server.py) │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │   API Cache (FastAPI)    │
     │   data.gov.in / IMD /    │
     │   Agmarknet / eNAM       │
     └──────────────────────────┘
```

## Agents

| Agent | Role | Model |
|-------|------|-------|
| **Orchestrator** | Intent routing, parameter extraction, LoopAgent refinement | `gemini-2.5-flash` |
| **Crop Advisor** | Soil-crop-climate recommendations from knowledge base | `gemini-2.5-flash` |
| **Scheme Finder** | Government scheme eligibility matching | `gemini-2.5-flash` |
| **Weather Planner** | 7-day forecast + agricultural action plan | `gemini-2.5-flash` |
| **Market Price** | Real-time mandi prices + MSP comparison | `gemini-2.5-flash` |

## Quick Start

```bash
# 1. Clone & configure
cp .env.example .env
# Edit .env with your API keys

# 2. Install dependencies
pip install uv
uv pip install -r requirements.txt

# 3. Run the MCP server
uv run python mcp/kisan_mcp_server.py

# 4. Run the orchestrator
uv run python agents/orchestrator.py
```

## Docker

```bash
docker-compose up --build
```

## Evaluation

```bash
# Run the 100-case regression test suite
python evals/run_evals.py
```

## Project Structure

```
kisan-saathi/
├── agents/                  # ADK Agent definitions
│   ├── orchestrator.py      # Root orchestrator (intent router)
│   ├── crop_advisor.py      # Crop advisory sub-agent
│   ├── scheme_finder.py     # Government scheme sub-agent
│   ├── weather_planner.py   # Weather planning sub-agent
│   └── market_price.py      # Market price sub-agent
├── mcp/                     # FastMCP server + tools
│   ├── kisan_mcp_server.py  # MCP server entrypoint
│   ├── models.py            # Pydantic data models
│   ├── api_cache.py         # FastAPI caching proxy
│   └── tools/               # Individual MCP tools
├── data/                    # Knowledge bases & static data
├── security/                # Input/output guards & audit
├── evals/                   # Evaluation framework
├── notebooks/               # Demo notebooks
└── docs/                    # Documentation
```

## License

MIT
