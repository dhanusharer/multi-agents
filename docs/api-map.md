# Kisan Saathi (किसान साथी) — API Contracts & Map

This document catalogs all endpoints, payload models, and tool execution boundaries.

---

## 1. Application Web REST Endpoints

### 1. Chat Execution Endpoint (`POST /api/chat`)
*   **Purpose**: Runs the multi-agent orchestrator.
*   **Input Payload (Pydantic Model `ChatRequest`)**:
    *   `query` (str): Mandatory text input.
    *   `session_id` (str, default: `"default_session"`): Session ID to load/save profile state.
    *   `image_base64` (str, optional): Base64 encoded string representing leaf photo.
*   **Output Payload**:
    *   `success` (bool): Process completion status.
    *   `response` (str): Synthesized response text.
    *   `profile` (dict): Farmer's active state details.
    *   `stats` (dict): Server session query, tool call, and block stats.
*   **Dependencies**:
    *   [agents/orchestrator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/agents/orchestrator.py)
    *   [security/input_guard.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/input_guard.py)
    *   [security/output_validator.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/security/output_validator.py)

### 2. Session Update Endpoint (`POST /api/session/update`)
*   **Purpose**: Modifies farmer details in session memory.
*   **Input Payload (Pydantic Model `SessionUpdateRequest`)**:
    *   `session_id` (str): Target session ID.
    *   `updates` (dict): Key-value pairs matching profile attributes (e.g. `crop`, `land_holding_hectares`).
*   **Output Payload**:
    *   `success` (bool): Process status.
    *   `profile` (dict): The updated profile object.
*   **Dependencies**:
    *   `KisanSaathiOrchestrator.session_service`

### 3. Session Reset Endpoint (`POST /api/session/reset`)
*   **Purpose**: Resets session details back to defaults.
*   **Input Payload (Pydantic Model `SessionResetRequest`)**:
    *   `session_id` (str): Target session ID.
*   **Output Payload**:
    *   `success` (bool): Process status.
    *   `profile` (dict): Re-initialized profile object.
*   **Dependencies**:
    *   `KisanSaathiOrchestrator.session_service`

### 4. Cached Mandi Prices (`GET /api/mandi-prices/{commodity}`)
*   **Purpose**: Fetches commodity prices from the caching layer.
*   **URL Path Parameter**: `commodity` (str)
*   **Query Parameters**: `state` (str, optional), `district` (str, optional)
*   **Output Payload**:
    *   `prices` (list): Array of matching mandi records.
    *   `cached` (bool): Indicates if the data was served from the cache.
    *   `source` (str): Identifies the source (e.g. `data.gov.in`, `local_fallback`).
*   **Dependencies**:
    *   [mcp_server/tools/market_tool.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/tools/market_tool.py)

### 5. Cached Weather Forecast (`GET /api/weather/{location}`)
*   **Purpose**: Fetches forecasts for coordinate points.
*   **URL Path Parameter**: `location` (str, e.g. `"13.34,77.10"`)
*   **Query Parameter**: `days` (int, default: `7`)
*   **Output Payload**:
    *   `weather` (dict): Forecast records.
    *   `cached` (bool): Indicates if data was served from the cache.
*   **Dependencies**:
    *   [mcp_server/tools/weather_tool.py](file:///c:/Users/DHANUSH%20A%20G/.gemini/antigravity/scratch/kisan-saathi/mcp_server/tools/weather_tool.py)

---

## 2. Model Context Protocol Tools

### 1. Crop Advisory Tool (`get_crop_advisory_tool`)
*   **Registered Schema**:
    *   *Inputs*: `crop` (str), `state` (str), `season` (str), `symptom` (str), `session_id` (str)
    *   *Outputs*: `GetCropAdvisoryOutput` (structured Pydantic JSON).
*   **Security Controls**: Sanitizes symptoms and runs InputGuard safety validation.

### 2. Scheme Eligibility Tool (`check_scheme_eligibility_tool`)
*   **Registered Schema**:
    *   *Inputs*: `land_holding_hectares` (float), `annual_income_rupees` (int), `age` (int), `state` (str), `is_sc_st` (bool), `is_disability` (bool), `is_income_tax_payer` (bool), `session_id` (str)
    *   *Outputs*: `CheckSchemeEligibilityOutput` (structured Pydantic JSON).

### 3. Weather Advisory Tool (`get_weather_advisory_tool`)
*   **Registered Schema**:
    *   *Inputs*: `crop` (str), `latitude` (float), `longitude` (float), `session_id` (str)
    *   *Outputs*: `GetWeatherAdvisoryOutput` (structured Pydantic JSON).

### 4. Market Price Tool (`get_market_price_tool`)
*   **Registered Schema**:
    *   *Inputs*: `commodity` (str), `state` (str), `district` (str), `session_id` (str)
    *   *Outputs*: `GetMarketPriceOutput` (structured Pydantic JSON).
