# Kisan Saathi (किसान साथी) — Dependency Graph & Critical Files

This document maps the imports, relationships, and risk profiles of all files within Kisan Saathi.

---

## 1. Import Hierarchy & Dependencies

### Web Entrypoint & API Caching Layer
*   **[main.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/main.py)**
    *   *Depends On*: `mcp_server/api_cache.py` (via `uvicorn.run("mcp_server.api_cache:app")`).
*   **[mcp_server/api_cache.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/api_cache.py)**
    *   *Depends On*: `agents/orchestrator.py:KisanSaathiOrchestrator`
    *   *Depends On*: Pydantic models in `mcp_server/models.py`

### Agent Orchestration Layer
*   **[agents/orchestrator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/orchestrator.py)**
    *   *Depends On*: Sub-agents: `agents/crop_advisor.py`, `agents/scheme_finder.py`, `agents/weather_planner.py`, `agents/market_price.py`.
    *   *Depends On*: Security modules: `security/input_guard.py`, `security/output_validator.py`, `security/audit_log.py`.
    *   *Depends On*: Tool interfaces in `mcp_server/kisan_mcp_server.py`.
*   **[agents/crop_advisor.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/crop_advisor.py)**
    *   *Depends On*: `mcp_server/tools/crop_tool.py:get_crop_advisory`
*   **[agents/scheme_finder.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/scheme_finder.py)**
    *   *Depends On*: `mcp_server/tools/scheme_tool.py:check_scheme_eligibility`
*   **[agents/weather_planner.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/weather_planner.py)**
    *   *Depends On*: `mcp_server/tools/weather_tool.py:get_weather_advisory`
*   **[agents/market_price.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/market_price.py)**
    *   *Depends On*: `mcp_server/tools/market_tool.py:get_market_price`

### FastMCP Tool Server Layer
*   **[mcp_server/kisan_mcp_server.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/kisan_mcp_server.py)**
    *   *Depends On*: Tool modules under `mcp_server/tools/`.
    *   *Depends On*: Security modules: `security/input_guard.py`, `security/output_validator.py`, `security/audit_log.py`.
*   **[mcp_server/tools/crop_tool.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/tools/crop_tool.py)**
    *   *Depends On*: `data/crop_advisory_kb.json`
*   **[mcp_server/tools/scheme_tool.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/tools/scheme_tool.py)**
    *   *Depends On*: `data/scheme_rules.json`
*   **[mcp_server/tools/market_tool.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/tools/market_tool.py)**
    *   *Depends On*: `data/msp_2025_26.json`

---

## 2. Core & High Impact Files (Do Not Modify Lightly)

### 1. [agents/orchestrator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/orchestrator.py) (System Core)
*   *Why*: Manages the central loop, detects regional languages, extracts key parameters, processes base64 visual diagnoses, and synthesizes agent responses.
*   *Risk*: Changes to regex parsers or translation layouts can break language detection or intent classification, causing evaluation harness failures.

### 2. [security/input_guard.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/input_guard.py) (Security Layer)
*   *Why*: Implements regex patterns and heuristic density checks to block prompt injections and redact PII.
*   *Risk*: Editing injection patterns or suspicious word lists may introduce security vulnerabilities or cause false-positive blocks, reducing the system's overall evaluation score.

### 3. [security/output_validator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/output_validator.py) (Output Guard)
*   *Why*: Scans agent outputs to block non-whitelisted domains, credentials, and code blocks.
*   *Risk*: Adding strict rules or blocking common words could cause safe responses to fail validation, falling back to error messages unnecessarily.

### 4. [mcp_server/kisan_mcp_server.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/kisan_mcp_server.py) (Tool Handler)
*   *Why*: Defines and exposes FastMCP tool interfaces to sub-agents.
*   *Risk*: Changing method signatures or type annotations (Pydantic schema definitions) can prevent sub-agents from calling the tools successfully.
