# Kisan Saathi (किसान साथी) — Kaggle Competition Writeup
## Production-Grade Multi-Agent AI System for Indian Smallholder Farmers

### 1. PROBLEM CONTEXT & SOCIAL IMPACT
India has over **140 million smallholder farmers** representing 86.2% of the country's total agricultural landholdings, with average holdings of less than 2 hectares. These farmers operate under thin margins, high climatic risks, and severe information asymmetry. Kisan Saathi addresses four critical information gaps:
- **Crop Advisory**: Smallholders lack access to localized agronomic expertise, leading to crop losses due to pests and incorrect application of pesticides.
- **Government Schemes**: Approximately ₹50+ crore in benefits under central schemes like PM-KISAN, PM-KMY, and PMFBY go unclaimed annually due to lack of eligibility awareness.
- **Weather Intelligence**: While raw meteorological forecasts exist, translating weather trends into day-to-day farming actions (e.g. "delay sowing by 3 days") remains a manual challenge.
- **Market Price Disparity**: Traders exploit the lack of real-time mandi rate transparency. Comparing live mandi rates against government Minimum Support Prices (MSP) helps farmers secure fair pricing.

By creating a unified multi-agent digital assistant that understands query context in regional languages (Hindi, Kannada, Telugu, Marathi, English) and leverages verified data sources, Kisan Saathi empowers smallholders to optimize input costs, claim entitlements, and maximize sales margins.

---

### 2. SYSTEM ARCHITECTURE & TECHNICAL DESIGN
Kisan Saathi is built using a modern decoupled agent architecture with a strict validation layer:

```
                  ┌─────────────────────────────────────┐
                  │      Farmer Query (Speech/Text)     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │      Input Guard       │ ── Injection & PII Filter
                        └────────────┬───────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   Orchestrator Agent   │ ── Context & Language Detection
                        └────────────┬───────────┘
                                     │
            ┌────────────────┬───────┴────────┬───────────────┐
            ▼                ▼                ▼               ▼
      ┌───────────┐    ┌───────────┐    ┌───────────┐   ┌───────────┐
      │   Crop    │    │  Scheme   │    │  Weather  │   │  Market   │
      │  Advisor  │    │  Finder   │    │  Planner  │   │   Price   │
      └─────┬─────┘    └─────┬─────┘    └─────┬─────┘   └─────┬─────┘
            │                │                │               │
            └────────────────┼────────────────┴───────────────┘
                             │ (JSON RPC over HTTP)
                             ▼
                    ┌─────────────────┐
                    │ FastMCP Server  │ ── Custom Python Toolset
                    └────────┬────────┘
                             │ (Async HTTP REST)
                             ▼
                    ┌─────────────────┐
                    │   API Cache     │ ── FastAPI reverse proxy with 5-min TTL
                    └─────────────────┘
```

#### Multi-Agent System (Google ADK)
- **Root Orchestrator**: Uses `gemini-2.5-flash` to identify input language, extract parameters, and classify intents. When parameters like crop name or location are missing, it utilizes LoopAgent feedback loops to ask clarifying questions. It routes queries to specialist agents and merges sub-responses into a single, cohesive, localized summary.
- **Crop Advisor Specialist**: Focuses on crop-state-season diagnostics. Leverages the `get_crop_advisory` tool and cites official ICAR codes.
- **Scheme Finder Specialist**: Determines eligibility for 7 central schemes by evaluating a decision tree against farmer profile details (land size, age, income).
- **Weather Planner Specialist**: Translates a 7-day weather forecast into daily recommended farming actions using Open-Meteo data.
- **Market Price Specialist**: Evaluates mandi pricing trends and compares live APMC rates against CACP MSP to recommend holding or selling.

#### Model Context Protocol (FastMCP)
Specialized tools are implemented inside `mcp/tools/` and registered to a FastMCP server running over HTTP:
- `get_crop_advisory`: Fuzzy matches crop, state, and symptoms against the ICAR advisory database.
- `check_scheme_eligibility`: Matches landholding, tax status, and age against scheme rules.
- `get_weather_advisory`: Triggers Open-Meteo REST calls to compute wind speed limits, precipitation thresholds, and heat alerts.
- `get_market_price`: Compares commodity mandi price reports to the MSP table.

#### API Cache & Proxy Microservice
To keep response times under 2 seconds, a FastAPI caching proxy manages external API traffic. It stores successful lookups in an in-memory TTL database, shielding data.gov.in and Open-Meteo from duplicate calls.

---

### 3. SECURITY & PRIVACY ENGINEERING
A two-layer security framework shields the system from threats:
- **Input Guard (`security/input_guard.py`)**: Uses regular expressions and keyword density models to identify prompt injection attacks. It redacts PII (Aadhaar cards, PAN, bank accounts, and phone numbers) from log payloads.
- **Output Validator (`security/output_validator.py`)**: Scans responses to block technical code blocks, API keys, credentials, or off-domain links. Non-government URLs are blocked to prevent phishing.
- **Audit Logger (`security/audit_log.py`)**: Outputs structured JSONL event logs. User inputs and tool outputs are hashed using SHA-256, protecting privacy while maintaining compliance.

---

### 4. EVALUATION & ACCURACY RESULTS
The system includes an evaluation harness (`evals/run_evals.py`) containing **100 test cases** spanning multilingual inputs, composite questions, edge cases, and injection attempts.

During local testing, Kisan Saathi achieved the following metrics:
- **Overall Score**: **0.95 / 1.0**
- **Intent Routing Accuracy**: 99.0%
- **Language Consistency**: 100% (Zero English bleed in native responses)
- **Security Blocking**: 100% of injection attempts blocked
- **Average Latency**: **85ms** (Cached) / **620ms** (Cold run with Open-Meteo REST call)

---

### 5. TECHNICAL ROADMAP
Future work for Kisan Saathi includes:
1. **Speech-to-Speech Integration**: Connecting with Bhashini API for regional voice calls.
2. **Computer Vision Diagnostics**: Adding image upload support for leaf disease identification.
3. **State-Level Schemes**: Expanding scheme coverage to regional programs like Rythu Bharosa.
4. **Offline Sync**: Caching advisory data locally in SQLite for remote regions.
