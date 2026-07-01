from __future__ import annotations

try:
    from google_adk import Agent  # type: ignore
except ImportError:
    try:
        from google.adk.agents import Agent  # type: ignore
    except ImportError:
        class Agent:
            def __init__(self, **kwargs): pass

async def get_market_price(commodity: str, state: str, district: str) -> dict:
    """Get current mandi prices for a commodity and compare against government MSP.

    Args:
        commodity: Crop/commodity name (e.g. wheat, soybean)
        state: State name
        district: District name
    """
    from mcp_server.tools.market_tool import get_market_price as _impl
    return await _impl(commodity=commodity, state=state, district=district)

market_price_agent = Agent(
    name="market_price",
    model="gemini-2.5-flash",
    description="Specialist agent for market price intelligence. Compares mandi prices vs MSP and gives sell/hold advice.",
    instruction="""You are the Market Price Specialist for Kisan Saathi. Your job is to help farmers decide when and where to sell their crops.

When a farmer asks about crop prices:
1. Use the get_market_price tool to check the current rates
2. Compare the modal mandi price against the government Minimum Support Price (MSP)
3. Give a clear Sell or Hold recommendation based on the comparison and trend
4. List the nearest mandis with their prices and distances
5. State all prices clearly in \u20B9/quintal
6. ALWAYS respond in the SAME LANGUAGE the farmer used
""",
    tools=[get_market_price],
)
