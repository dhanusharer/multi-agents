# Kisan Saathi (किसान साथी) — System Architecture Map

This document outlines the system topology, component interactions, and data paths of Kisan Saathi.

---

## 1. System Topology Overview

Kisan Saathi is a decentralized service composed of an orchestration layer, specialized agent microservices, a FastMCP tool runner, and a web-based dashboard caching proxy.

```
+----------------------------------------------------------------------------------------+
|                                  FARMER BROWSER CLIENT                                 |
+------------------------------------------┬---------------------------------------------+
                                           │ (HTTP REST /api/chat)
                                           ▼
+----------------------------------------------------------------------------------------+
|                        API CACHE & WEB SERVER (api_cache.py:8001)                      |
|  - Serves HTML5 SPA Dashboard at "/"                                                   |
|  - Validates query with InputGuard                                                     |
|  - Instantiates KisanSaathiOrchestrator and InMemorySessionService                     |
|  - Performs TTL Caching (5-min RAM dict) for Open-Meteo & data.gov.in REST calls       |
+------------------------------------------┬---------------------------------------------+
                                           │ (Sub-agent delegate call)
                                           ▼
+----------------------------------------------------------------------------------------+
|                        GOOGLE ADK AGENT ENGINE (orchestrator.py)                       |
|  - Identifies language (Devanagari, Kannada, Telugu scripts & Hinglish transliteration)  |
|  - Classifies intent (Crop, Scheme, Weather, Market, General)                          |
|  - Extracts farming parameters (Crop, State, District, Land)                           |
|  - Runs Multimodal Visual Pathologist (Gemini 2.5 Flash for leaf image analysis)       |
|  - Evaluates missing parameters and returns clarifying questions                      |
|  - Coordinates Specialist Sub-agents and merges responses                             |
+------------------------------------------┬---------------------------------------------+
                                           │ (Imports & wraps wrapped tools)
                                           ▼
+----------------------------------------------------------------------------------------+
|                       FASTMCP TOOLS SERVER (kisan_mcp_server.py:8000)                  |
|  - Runs FastMCP over HTTP transport                                                    |
|  - Wraps tools with InputGuard validating args, AuditLogger capturing execution runs   |
+------------------------------------------┬---------------------------------------------+
                                           │ (Asynchronous REST & file operations)
                                           ▼
           ┌───────────────────────┬───────┴───────┬───────────────────────┐
           ▼                       ▼               ▼                       ▼
+---------------------+ +--------------------+ +--------------------+ +--------------------+
|  CROP ADVISOR TOOL  | |SCHEME ELIGIBILITY  | |  WEATHER FORECAST  | | MANDI PRICE TOOL   |
|   (crop_tool.py)    | | (scheme_tool.py)   | |  (weather_tool.py) | |  (market_tool.py)  |
|  Matches symptoms   | | Evaluates profile  | | Fetches Open-Meteo | | Fetches APMC REST  |
|  against ICAR DB    | | against 7 rules    | | 7-day REST forecasts| | & compares MSP db  |
+----------┬----------+ +---------┬----------+ +---------┬----------+ +---------┬----------+
           │                       │                       │                       │
           ▼                       ▼                       ▼                       ▼
+---------------------+ +--------------------+ +--------------------+ +--------------------+
|  crop_advisory_kb   | |   scheme_rules     | |   Open-Meteo REST  | | data.gov.in REST   |
|     (JSON DB)       | |     (JSON DB)      | |  (External API)    | |  (External API)    |
|                     | |                    | |                    | | msp_2025_26 JSON   |
+---------------------+ +--------------------+ +--------------------+ +--------------------+
```

---

## 2. Core Components

### 1. Web & Proxy Layer ([mcp_server/api_cache.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/api_cache.py))
*   **Web Server**: Bootstrapped via FastAPI on port `8001`. Serves the dashboard client, session controls, and chat APIs.
*   **API Caching**: Intercepts external weather and market prices. Stores results in a global `_cache` dictionary (keys are generated from commodity names and location coordinates). Entries expire after a TTL of 300 seconds.

### 2. Multi-Agent Orchestration Layer ([agents/orchestrator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/orchestrator.py))
*   **KisanSaathiOrchestrator**: The central controller coordinating the agents. It manages the agent loop, extracts parameters, identifies regional languages, performs visual diagnostics on leaf photos, and formats response templates.
*   **Specialist Sub-agents**:
    *   `crop_advisor_agent` (driven by `agents/crop_advisor.py`): Compiles pest and disease diagnostics citing official ICAR codes.
    *   `scheme_finder_agent` (driven by `agents/scheme_finder.py`): Discover government schemes matching farmer profiles.
    *   `weather_planner_agent` (driven by `agents/weather_planner.py`): Translates meteorological forecasts into daily farming actions.
    *   `market_price_agent` (driven by `agents/market_price.py`): Compares APMC mandi prices against Government Minimum Support Prices (MSP).

### 3. Model Context Protocol Layer ([mcp_server/kisan_mcp_server.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/kisan_mcp_server.py))
*   **FastMCP Server**: Exposes internal python tools to agents using the standardized MCP JSON-RPC protocol over HTTP.
*   **Auditing and Input Gates**: Before executing any tool, it validates arguments using `InputGuard` and logs execution metadata (input hash, output hash, latency, status) using `AuditLogger`.

### 4. Security Layer ([security/](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/))
*   **Input Guard**: Intercepts prompt injections and redacts personally identifiable information (PII) like Aadhaar, PAN, phone numbers, and bank accounts.
*   **Output Validator**: Scans synthesized responses to block non-governmental links, credentials, and code blocks before returning them.

---

## 3. Data Integration & External APIs
*   **Mandi Prices**: Fetched via the Agmarknet API on data.gov.in. If no API key is configured, the system falls back to cached prices stored in `CACHED_MANDI_PRICES` inside `market_tool.py`.
*   **Weather Forecasts**: Fetched in real-time from the Open-Meteo REST API using coordinates resolved from district names.
*   **Visual Diagnoses**: The orchestrator parses base64 image strings and calls the Gemini Multimodal API with a pathology prompt to identify the crop type and symptoms.
