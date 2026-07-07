from __future__ import annotations
from fastmcp import FastMCP
from mcp_server.tools.crop_tool import get_crop_advisory
from mcp_server.tools.scheme_tool import check_scheme_eligibility
from mcp_server.tools.weather_tool import get_weather_advisory
from mcp_server.tools.market_tool import get_market_price
from security.input_guard import InputGuard
from security.output_validator import OutputValidator
from security.audit_log import AuditLogger
import time
import os

# Initialize FastMCP Server
mcp = FastMCP(
    name="kisan_mcp",
    instructions=(
        "Kisan Saathi MCP Server — provides agricultural tools for "
        "crop advisory, scheme lookup, weather forecasting, and market prices."
    )
)

# Initialize Security Objects
input_guard = InputGuard()
output_validator = OutputValidator()
audit_log = AuditLogger()

@mcp.tool()
async def get_crop_advisory_tool(
    crop: str,
    state: str,
    season: str,
    symptom: str,
    session_id: str = "default_session"
) -> dict:
    """Get ICAR-validated crop advisory for pest/disease management.

    Args:
        crop: Crop name (e.g., rice, wheat, tomato)
        state: State name (e.g., Karnataka, Maharashtra, Punjab)
        season: Growing season - kharif or rabi
        symptom: Observed plant symptom or disease name
        session_id: Unique farmer session ID for tracking
    
    Returns:
        Structured crop advisory dict.
    """
    start_time = time.time()
    
    # 1. Input Guard checking
    is_safe, error_reason = input_guard.validate_query(f"{crop} {symptom}")
    if not is_safe:
        audit_log.log_security_event(session_id, "input_injection", error_reason or "Potential injection", True)
        return {"error": "Input safety validation failed."}

    # 2. Tool Execution
    try:
        result = await get_crop_advisory(crop, state, season, symptom)
        success = True
    except Exception as e:
        result = {"error": f"Tool execution failed: {str(e)}"}
        success = False

    latency = (time.time() - start_time) * 1000
    
    # 3. Audit logging
    audit_log.log_tool_call(
        session_id=session_id,
        agent_name="crop_advisor",
        tool_name="get_crop_advisory",
        input_dict={"crop": crop, "state": state, "season": season, "symptom": symptom},
        output_dict=result,
        success=success,
        latency_ms=latency
    )
    
    return result

@mcp.tool()
async def check_scheme_eligibility_tool(
    land_holding_hectares: float,
    annual_income_rupees: int,
    age: int,
    state: str,
    is_sc_st: bool = False,
    is_disability: bool = False,
    is_income_tax_payer: bool = False,
    session_id: str = "default_session"
) -> dict:
    """Check farmer eligibility against 7 major government schemes.

    Args:
        land_holding_hectares: Total land holding in hectares
        annual_income_rupees: Annual family income in INR
        age: Age of the farmer in years
        state: State of residence
        is_sc_st: Whether farmer belongs to Scheduled Caste / Scheduled Tribe
        is_disability: Whether farmer has a disability
        is_income_tax_payer: Whether farmer is an income tax payer
        session_id: Unique farmer session ID for tracking

    Returns:
        Eligible and ineligible schemes.
    """
    start_time = time.time()
    
    try:
        result = await check_scheme_eligibility(
            land_holding_hectares,
            annual_income_rupees,
            age,
            state,
            is_sc_st,
            is_disability,
            is_income_tax_payer
        )
        success = True
    except Exception as e:
        result = {"error": f"Tool execution failed: {str(e)}"}
        success = False

    latency = (time.time() - start_time) * 1000
    
    audit_log.log_tool_call(
        session_id=session_id,
        agent_name="scheme_finder",
        tool_name="check_scheme_eligibility",
        input_dict={
            "land_holding_hectares": land_holding_hectares,
            "annual_income_rupees": annual_income_rupees,
            "age": age,
            "state": state
        },
        output_dict=result,
        success=success,
        latency_ms=latency
    )
    
    return result

@mcp.tool()
async def get_weather_advisory_tool(
    crop: str,
    latitude: float,
    longitude: float,
    session_id: str = "default_session"
) -> dict:
    """Fetch 7-day weather forecast and generate agricultural advisories.

    Args:
        crop: Crop name (e.g. wheat, rice)
        latitude: Location latitude
        longitude: Location longitude
        session_id: Unique farmer session ID for tracking

    Returns:
        7-day weather daily forecast and crop action plan.
    """
    start_time = time.time()
    
    try:
        result = await get_weather_advisory(crop, latitude, longitude)
        success = True
    except Exception as e:
        result = {"error": f"Tool execution failed: {str(e)}"}
        success = False

    latency = (time.time() - start_time) * 1000
    
    audit_log.log_tool_call(
        session_id=session_id,
        agent_name="weather_planner",
        tool_name="get_weather_advisory",
        input_dict={"crop": crop, "latitude": latitude, "longitude": longitude},
        output_dict=result,
        success=success,
        latency_ms=latency
    )
    
    return result

@mcp.tool()
async def get_market_price_tool(
    commodity: str,
    state: str,
    district: str,
    session_id: str = "default_session"
) -> dict:
    """Get current mandi prices for a commodity and compare against government MSP.

    Args:
        commodity: Crop/commodity name (e.g. wheat, soybean)
        state: State name
        district: District name
        session_id: Unique farmer session ID for tracking

    Returns:
        Mandi prices with MSP comparison.
    """
    start_time = time.time()
    
    try:
        result = await get_market_price(commodity, state, district)
        success = True
    except Exception as e:
        result = {"error": f"Tool execution failed: {str(e)}"}
        success = False

    latency = (time.time() - start_time) * 1000
    
    audit_log.log_tool_call(
        session_id=session_id,
        agent_name="market_price",
        tool_name="get_market_price",
        input_dict={"commodity": commodity, "state": state, "district": district},
        output_dict=result,
        success=success,
        latency_ms=latency
    )
    
    return result

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
