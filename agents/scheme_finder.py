from __future__ import annotations

try:
    from google_adk import Agent  # type: ignore
except ImportError:
    try:
        from google.adk.agents import Agent  # type: ignore
    except ImportError:
        class Agent:
            def __init__(self, **kwargs): pass

async def check_scheme_eligibility(
    land_holding_hectares: float,
    annual_income_rupees: int,
    age: int,
    state: str,
    is_sc_st: bool = False,
    is_disability: bool = False,
    is_income_tax_payer: bool = False
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
    """
    from mcp_server.tools.scheme_tool import check_scheme_eligibility as _impl
    return await _impl(
        land_holding_hectares=land_holding_hectares,
        annual_income_rupees=annual_income_rupees,
        age=age,
        state=state,
        is_sc_st=is_sc_st,
        is_disability=is_disability,
        is_income_tax_payer=is_income_tax_payer
    )

scheme_finder_agent = Agent(
    name="scheme_finder",
    model="gemini-2.5-flash",
    description="Specialist agent for government scheme discovery. Matches farmer profile against scheme eligibility rules.",
    instruction="""You are the Scheme Finder for Kisan Saathi. Your job is to check government scheme eligibility for farmers.

When a farmer asks about schemes:
1. Use the check_scheme_eligibility tool to evaluate eligibility for all 7 central schemes
2. For eligible schemes, output the name, benefits, and CLEAR step-by-step registration instructions in the farmer's language
3. Highlight the required documents so they know exactly what to prepare
4. For ineligible schemes, briefly explain the exclusion reason (e.g. "land holding exceeds 2 hectares") if asked or if it is helpful context
5. NEVER make up scheme benefits, criteria, or websites
6. ALWAYS respond in the SAME LANGUAGE the farmer used
""",
    tools=[check_scheme_eligibility],
)
