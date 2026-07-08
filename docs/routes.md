# Kisan Saathi (किसान साथी) — Routing Map

This document registers all routes, UI layout components, and backend API endpoints within Kisan Saathi.

---

## 1. Application Layout & UI Pages
Since the application uses a Single Page App (SPA) design, there is a single main page layout served by the server.

*   **Main Route**: `GET /`
    *   **File**: [mcp_server/api_cache.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/api_cache.py) (served via the `home()` method as an `HTMLResponse`).
    *   **Layout Structure**:
        *   **Header**: Contains the application title (*Kisan Saathi* / *किसान साथी*) and an active status badge showing connection metrics.
        *   **Main Sidebar**: Contains a profile manager form that allows users to view and update the farmer's active details (state, district, crop, land size, tax status).
        *   **Chat Section**: Contains the conversational message list and an input area supporting text queries, quick-action suggestions, and base64 leaf photo uploads.

---

## 2. API Endpoints Table

| Method | Endpoint | Purpose | Request Payload | Response Schema | Auth |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/` | Serves dashboard SPA. | None | `HTMLResponse` | None |
| **GET** | `/health` | Returns service status and cache metrics. | None | `{"status": "ok", "service": "kisan-api-cache", "cached_items": int}` | None |
| **POST** | `/api/chat` | Runs orchestrator workflow. | `ChatRequest` (JSON) | `{"success": bool, "response": str, "profile": dict, "stats": dict}` | None |
| **POST** | `/api/session/update` | Updates active profile attributes. | `SessionUpdateRequest` | `{"success": bool, "profile": dict}` | None |
| **POST** | `/api/session/reset` | Resets active profile state. | `SessionResetRequest` | `{"success": bool, "profile": dict}` | None |
| **GET** | `/api/mandi-prices/{commodity}`| Proxies mandi prices. | URL params (`state`, `district`) | `{"prices": list, "cached": bool, "source": str}` | None |
| **GET** | `/api/weather/{location}` | Proxies Open-Meteo forecasts. | URL param (`days`) | `{"weather": dict, "cached": bool}` | None |

---

## 3. Tool Route Bindings (Model Context Protocol)
MCP tools are registered on the FastMCP tool server using HTTP JSON-RPC wrappers:

*   **Tool**: `get_crop_advisory_tool`
    *   *Parameters*: `crop` (str), `state` (str), `season` (str), `symptom` (str), `session_id` (str)
    *   *Target Implementation*: `mcp_server/tools/crop_tool.py:get_crop_advisory`
*   **Tool**: `check_scheme_eligibility_tool`
    *   *Parameters*: `land_holding_hectares` (float), `annual_income_rupees` (int), `age` (int), `state` (str), `is_sc_st` (bool), `is_disability` (bool), `is_income_tax_payer` (bool), `session_id` (str)
    *   *Target Implementation*: `mcp_server/tools/scheme_tool.py:check_scheme_eligibility`
*   **Tool**: `get_weather_advisory_tool`
    *   *Parameters*: `crop` (str), `latitude` (float), `longitude` (float), `session_id` (str)
    *   *Target Implementation*: `mcp_server/tools/weather_tool.py:get_weather_advisory`
*   **Tool**: `get_market_price_tool`
    *   *Parameters*: `commodity` (str), `state` (str), `district` (str), `session_id` (str)
    *   *Target Implementation*: `mcp_server/tools/market_tool.py:get_market_price`
