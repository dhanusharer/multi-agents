from __future__ import annotations

try:
    from google_adk import Agent  # type: ignore
except ImportError:
    try:
        from google.adk.agents import Agent  # type: ignore
    except ImportError:
        class Agent:
            def __init__(self, **kwargs): pass

async def get_weather_advisory(crop: str, latitude: float, longitude: float) -> dict:
    """Fetch 7-day weather forecast and generate agricultural advisories.

    Args:
        crop: Crop name (e.g. wheat, rice)
        latitude: Location latitude
        longitude: Location longitude
    """
    from mcp_server.tools.weather_tool import get_weather_advisory as _impl
    return await _impl(crop=crop, latitude=latitude, longitude=longitude)

weather_planner_agent = Agent(
    name="weather_planner",
    model="gemini-2.5-flash",
    description="Specialist agent for weather-based agricultural planning. Translates forecasts into actions.",
    instruction="""You are the Weather Planner for Kisan Saathi. Your job is to translate weather forecasts into actionable advice.

When a farmer asks about weather or planting conditions:
1. Use the get_weather_advisory tool to get weather details and recommendations
2. Summarize the 7-day weather forecast in simple, farmer-friendly terms (do not just repeat numbers)
3. Provide day-by-day action recommendations (e.g. "Tomorrow is dry, perfect for weeding. Delay spraying pesticide on Wednesday due to high wind.")
4. Call out risk alerts (e.g. frost warning, waterlogging warning, rain interruption) in bold
5. ALWAYS respond in the SAME LANGUAGE the farmer used
""",
    tools=[get_weather_advisory],
)
