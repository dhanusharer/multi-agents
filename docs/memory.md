# Kisan Saathi (किसान साथी) — Project Memory & System Brain

This document acts as the single source of truth for the Kisan Saathi codebase, outlining its business logic, software architecture, technical decisions, data schema, and development workflow.

---

## 1. Project Overview
Kisan Saathi is a production-grade, multi-agent AI assistant built to serve India's 140 million smallholder farmers. The system is designed to process complex agricultural questions (such as crop advisory, weather forecasts, market prices, and government scheme eligibility) in multiple regional Indian languages (Hindi, Kannada, Telugu, Marathi) and English. 

---

## 2. Business Purpose
*   **Target User**: Indian smallholder farmers (specifically the 86.2% who cultivate less than 2 hectares of land).
*   **Problem Solved**: Smallholder farmers face major information asymmetries. They lose yields due to pests and incorrect pesticide usage, lack visibility on real-time APMC mandi prices compared to government Minimum Support Prices (MSP), fail to claim central welfare benefits (such as PM-KISAN), and struggle to map weather forecasts to daily farming tasks.
*   **Core Value Proposition**: Kisan Saathi integrates disparate data sources into a single digital companion. It allows a farmer to submit a query—in text, transliterated Hinglish, or as a photo of a diseased leaf—and receive a personalized, research-backed response that integrates crop diagnosis, weather planning, market intelligence, and welfare enrollment.

---

## 3. Tech Stack
*   **Runtime**: Python 3.12 (standard virtual environment or docker-slim build).
*   **Orchestration Engine**: Google ADK (Agent Development Kit) `google-adk>=2.0` (drives agent routing, parameters extraction, and sub-agent bindings).
*   **Large Language Models (LLM)**: Gemini 2.5 Flash (`gemini-2.5-flash`) for intent routing, parameter parsing, leaf visual diagnoses, and response synthesis.
*   **Tooling Protocol**: Model Context Protocol (FastMCP) `fastmcp>=3.4.0` (asynchronous HTTP transport server).
*   **Web Services & Proxy**: FastAPI `fastapi>=0.115.0` (runs endpoints, cache layer, and dashboard) and Uvicorn `uvicorn>=0.30.0` (async HTTP web server).
*   **Client Interface**: Embedded Vanilla HTML5/CSS3 Single Page App (SPA) with custom micro-animations, theme gradients, and profile editing sidebars.
*   **Local Caches & Data Store**: Local JSON databases under `data/` and dictionary-based RAM caching.
*   **Deployment**: Antigravity Platform CLI (`antigravity.yaml`) and Docker Compose container configurations.

---

## 4. Repository Structure

```
kisan-saathi/
├── .github/workflows/          # CI/CD pipelines
│   └── evals.yml               # Runs evaluation suite on code changes
├── agents/                     # Google ADK agent configurations
│   ├── __init__.py             # Exposes agent definitions
│   ├── orchestrator.py         # Main intent router, extractor, and synthesizer
│   ├── crop_advisor.py         # Soil-crop advisor sub-agent
│   ├── scheme_finder.py        # Welfare scheme eligibility sub-agent
│   ├── weather_planner.py      # Weather-based action planning sub-agent
│   └── market_price.py         # Mandi price & MSP evaluator sub-agent
├── mcp_server/                 # FastMCP backend and Web layer
│   ├── __init__.py             # Package initializer
│   ├── kisan_mcp_server.py     # FastMCP server registration and secure tool wrapper
│   ├── api_cache.py            # FastAPI cache proxy, routing, and dashboard client
│   ├── models.py               # Pydantic data schemas representing tools outputs
│   └── tools/                  # Concrete tool business implementations
│       ├── __init__.py         # Package initializer
│       ├── crop_tool.py        # Local KB queries matching crops and symptoms
│       ├── market_tool.py      # Agmarknet live REST fetches + MSP comparator
│       ├── scheme_tool.py      # Entitlement decision-tree logic
│       └── weather_tool.py     # Open-Meteo live REST fetches + advisory compiler
├── data/                       # Local JSON databases
│   ├── crop_advisory_kb.json   # Research-grounded pest symptoms & ICAR treatments
│   ├── scheme_rules.json       # Eligibility limits, benefits, and steps for 7 schemes
│   └── msp_2025_26.json        # Government MSP limits & district coordinates
├── security/                   # Guardrails and compliance logs
│   ├── __init__.py             # Package initializer
│   ├── input_guard.py          # Prompt injection guards & PII filters
│   ├── output_validator.py     # Codeblock and off-domain URL validator
│   ├── audit_log.py            # Append-only hashed compliance event logger
│   └── audit_log.json          # Structured compliance logs
├── evals/                      # Agent accuracy testing harness
│   ├── run_evals.py            # Evaluator suite scoring language, safety, and grounding
│   ├── test_cases.json         # 100 structured test assertions
│   └── eval_results.json       # Metrics report output of the last evals run
├── notebooks/                  # Demo assets
│   └── kisan_saathi_demo.ipynb # Jupyter notebook demonstrating tools usage
└── docs/                       # Project documentation folder
    ├── brain.md                # System outline and architecture blueprint
    ├── memory.md               # Base operational knowledge base (this file)
    ├── architecture.md         # Detailed service map and system layout
    ├── routes.md               # API endpoints registry and view structures
    ├── api-map.md              # Detailed REST and MCP tool contracts
    ├── database-map.md         # Schema layouts for JSON database collections
    ├── dependency-graph.md     # Code import connections and high impact modules
    └── KAGGLE_WRITEUP.md       # Technical competition architectural writeup
```

---

## 5. System Architecture
Kisan Saathi splits tasks between an orchestrator, specialist agents, FastMCP tools, and a local cache/proxy microservice:

```
[Farmer Browser UI] 
       │ (REST /api/chat)
       ▼
[FastAPI Caching Proxy] (mcp_server/api_cache.py)
       │ (Evaluates InputGuard safety, checks session state)
       ▼
[Orchestrator Agent] (agents/orchestrator.py)
       ├─ Multimodal Image Diagnosis (Updates profile crop/symptoms)
       ├─ Language & Intent Detection
       ├─ Parameter Extraction (Normalizes acres to hectares)
       ├─ LoopAgent check (Clarifies missing variables if needed)
       │
       └─ Delegate to [Specialist Sub-agents] (agents/*)
                            │
                            ▼
                  [FastMCP Tool server] (mcp_server/kisan_mcp_server.py)
                            ├─ Runs InputGuard checks on tool arguments
                            ├─ Executes Tools (mcp_server/tools/*)
                            │    ├─ [crop_tool] ────> Reads [crop_advisory_kb.json]
                            │    ├─ [scheme_tool] ──> Reads [scheme_rules.json]
                            │    ├─ [weather_tool] ─> Fetches [Open-Meteo REST API]
                            │    └─ [market_tool] ──> Fetches [data.gov.in REST API] / [msp_2025_26.json]
                            │
                            └─ Writes hashed logs via [AuditLogger]
```

---

## 6. Routing Map
FastAPI routing is registered in [mcp_server/api_cache.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/api_cache.py):
*   `GET /`: Serves the HTML5/CSS3 farmer dashboard SPA. (Auth: None)
*   `GET /health`: Returns service health status and RAM cache size. (Auth: None)
*   `POST /api/chat`: Processes queries. Triggers InputGuard, runs Orchestrator Agent, checks output safety, and returns results. (Auth: None)
*   `POST /api/session/update`: Updates parameters in the active session. (Auth: None)
*   `POST /api/session/reset`: Resets active session back to default parameters. (Auth: None)
*   `GET /api/mandi-prices/{commodity}`: Proxies commodity prices. (Auth: None)
*   `GET /api/weather/{location}`: Proxies Open-Meteo forecasts. (Auth: None)

---

## 7. Frontend Architecture
The dashboard UI is served directly from the root route `/` of the FastAPI server. It is written as a Vanilla HTML5/CSS3 Single Page App (SPA) to ensure maximum speed and compatibility.
*   **Layout**: Built using CSS Flexbox and Grid. Styled with a dark, premium agricultural color scheme (accent greens, deep shadows, and subtle micro-animations).
*   **State Management**: Handled in-browser via JavaScript objects tracking the current `session_id` and the farmer's active `profile` (e.g. state, district, crop, and land size).
*   **API Client**: Communicates asynchronously with the backend endpoints using native JS `fetch()`. It handles image conversions to base64, updates chat histories, and syncs the profile editing sidebar.

---

## 8. Backend Architecture
The backend is structured into two main service layers:
1.  **FastAPI API Caching Layer**: Hosts endpoints, manages simple TTL in-memory caching, and acts as the entrypoint for web clients.
2.  **Google ADK Multi-Agent Layer**: Houses the orchestrator agent and specialized sub-agents. It performs language classification, parameters extraction, visual diagnosis, and merges agent outputs into a unified response.

---

## 9. Database Architecture
Kisan Saathi uses local, structured JSON files for data storage:
*   [crop_advisory_kb.json](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/data/crop_advisory_kb.json): Contains pests, Devanagari translation names, diagnostic symptoms, ICAR reference codes, and organic/chemical treatments.
*   [scheme_rules.json](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/data/scheme_rules.json): Documents eligibility parameters (landholding, age, income tax restrictions) and step-by-step registration instructions for 7 welfare schemes.
*   [msp_2025_26.json](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/data/msp_2025_26.json): Stores Minimum Support Prices (MSP) and coordinates (lat/lon) for Indian districts.

---

## 10. Authentication Flow
*   **No Authentication Implemented**: The system operates without credentials or accounts to reduce barriers for farmers.
*   **Session Tracking**: Sessions are tracked via a client-generated `session_id` passed in requests. This maps to an active profile stored in the server's `InMemorySessionService`.

---

## 11. API Inventory
*   `POST /api/chat`: Runs orchestrator. Accepts `query`, `session_id`, and `image_base64`. Returns synthesized response, active profile, and system metrics.
*   `POST /api/session/update`: Updates session state directly. Returns current profile.
*   `POST /api/session/reset`: Resets active farmer profile state.
*   `GET /api/mandi-prices/{commodity}`: Returns commodity prices. Falls back to offline database if no API key is set.
*   `GET /api/weather/{location}`: Returns Open-Meteo forecasts.

---

## 12. Data Flow Diagrams

### User Query Flow
```
User Action (Query/Image) ──> input_guard.py (Validate) ──> orchestrator.py (Extract Args)
                                                                   │
                                        ┌──────────────────────────┴──────────────────────────┐
                                        ▼                                                     ▼
                            Route to Specialist Sub-Agents                           Clarify Missing Variables
                                        │                                           (Crop or Location details)
                                        ▼
                            kisan_mcp_server.py Tools
                                        │
                                        ├─ crop_tool ──> Query crop_advisory_kb.json
                                        ├─ scheme_tool ─> Check scheme_rules.json
                                        ├─ weather_tool ─> Fetch Open-Meteo REST API
                                        └─ market_tool ──> Fetch data.gov.in REST API
                                        │
                                        ▼
                            Synthesize merged output response
                                        │
                                        ▼
                            output_validator.py (Validate) ──> Return HTTP 200 JSON
```

---

## 13. Environment Variables
*   `GOOGLE_API_KEY`: Required. Authenticates Gemini 2.5 Flash agents.
*   `DATA_GOV_IN_API_KEY`: Optional. Authenticates live Agmarknet REST fetches. If empty, falls back to offline JSON data.
*   `PORT`: Optional. The local port FastAPI binds to (defaults to `8001`).
*   `API_CACHE_URL`: Optional. URL pointing to the caching service (defaults to `http://localhost:8001`).

---

## 14. Third Party Integrations
*   **Open-Meteo API** (`https://api.open-meteo.com/v1/forecast`): Used to fetch 7-day weather forecasts for coordinate points.
*   **data.gov.in Agmarknet API** (`https://api.data.gov.in/resource/9ef84281-2261-4db5-936a-2dd27d8ebd9d`): Used to fetch mandi prices.
*   **Gemini Multimodal API**: Used to analyze leaf photos to identify crops and diseases.

---

## 15. Feature Inventory
1.  **Orchestrated Farmer Chat**: Language-detection, intent-classification, parameter extraction, and multi-agent synthesis.
2.  **Crop Disease Advisor**: Soil-crop diagnostic matching using ICAR research data.
3.  **Welfare Entitlements Engine**: Dynamic eligibility checks against 7 central government schemes.
4.  **Weather Action Planner**: Generates daily agricultural action recommendations based on meteorological forecasts.
5.  **Mandi Intelligence**: Real-time mandi rate evaluations with MSP comparisons and hold/sell advice.
6.  **Visual Diagnostics**: Automated crop and disease detection from uploaded leaf photos.
7.  **Audit Compliance**: Append-only event logger using SHA-256 hashes to log queries and tool runs securely.

---

## 16. Dependency Graph
*   `main.py` -> `mcp_server/api_cache.py` -> `agents/orchestrator.py`.
*   `agents/orchestrator.py` -> Specialist agents (`crop_advisor.py`, etc.) and `mcp_server/kisan_mcp_server.py`.
*   `mcp_server/kisan_mcp_server.py` -> Tool implementations (`crop_tool.py`, etc.) and security checks (`input_guard.py`, etc.).
*   `mcp_server/tools/*_tool.py` -> Local JSON databases under `data/`.

---

## 17. Important Files
*   [main.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/main.py): Starting script.
*   [mcp_server/api_cache.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/api_cache.py): API, cache proxy, and dashboard.
*   [agents/orchestrator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/orchestrator.py): Intent router and parameter extractor.
*   [mcp_server/kisan_mcp_server.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/kisan_mcp_server.py): Defines MCP tools.
*   [security/input_guard.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/input_guard.py): Prompt injection filters.
*   [security/output_validator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/output_validator.py): Scans outputs to prevent credential leaks and verify domain links.
*   [evals/run_evals.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/evals/run_evals.py): Evaluation regression harness.

---

## 18. Performance Notes
*   **Fast Caching**: The API cache proxy bypasses network calls, serving cached requests under 100ms.
*   **Hinglish Heuristics**: Custom regex patterns detect Hinglish terms directly, saving LLM tokens and reducing latency.

---

## 19. Technical Debt
*   **RAM Cache**: Bypasses persistent storage, meaning caching and active profiles reset on server restart.
*   **Docker Path Mismatch**: `Dockerfile` and `docker-compose.yml` contain paths referencing `mcp/` instead of `mcp_server/`. This causes container builds to crash unless modified.

---

## 20. Development Workflow
1.  **Local Execution**: Start microservices locally by running `python main.py`.
2.  **Extending Data**: Update JSON databases under `data/` to add crops, pests, or scheme rules.
3.  **Security Testing**: Run the evaluation harness (`python evals/run_evals.py`) to verify any changes to security patterns or templates.

---

## 21. Deployment Process
*   **Antigravity Deploy**: Managed via `antigravity.yaml` configuration.
*   **Docker Compose**: Build and launch services in separate containers: `fastmcp_server` on port 8000 and `api_cache` on port 8001.

---

## 22. Known Risks
*   **API Failures**: Rate limits or downtime on data.gov.in can block live market data. To mitigate this, tools fall back to pre-seeded cached variables.
*   **State Reset**: Restarting the cache server wipes current farmer session states, resetting active profile settings.

---

## 23. Future Recommendations
1.  **Persistent Storage**: Move cache and session state from RAM to a persistent SQLite database.
2.  **Docker Fix**: Correct the paths in `Dockerfile` and `docker-compose.yml` to prevent deployment crashes.
3.  **Expanded Regional Logic**: Add state-level schemes and localized rules to support more regional programs.
