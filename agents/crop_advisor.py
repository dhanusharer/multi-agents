from __future__ import annotations

try:
    from google_adk import Agent  # type: ignore
except ImportError:
    try:
        from google.adk.agents import Agent  # type: ignore
    except ImportError:
        class Agent:
            def __init__(self, **kwargs): pass

# Define the local tool wrapper function for ADK Agent
async def get_crop_advisory(crop: str, state: str, season: str, symptom: str) -> dict:
    """Get ICAR-validated crop advisory for pest/disease management.
    
    Args:
        crop: Crop name (e.g., rice, wheat, tomato)
        state: Indian state name
        season: Growing season - kharif or rabi
        symptom: Observed plant symptom or disease name
    
    Returns:
        Advisory with treatments, ICAR references, and irrigation advice.
    """
    from mcp_server.tools.crop_tool import get_crop_advisory as _impl
    return await _impl(crop=crop, state=state, season=season, symptom=symptom)

crop_advisor_agent = Agent(
    name="crop_advisor",
    model="gemini-2.5-flash",
    description="Expert crop advisor powered by ICAR research data. Diagnoses pests and diseases, recommends treatments.",
    instruction="""You are an expert crop advisor for Indian farmers, powered by ICAR (Indian Council of Agricultural Research) data.

When a farmer describes a crop issue or asks about a crop:
1. Use the get_crop_advisory tool to look up scientific advice.
2. Provide a highly comprehensive, rich, and detailed crop advisory response. Do not summarize briefly; output as much specific detail as possible from the tool's return values.
3. ALWAYS include and explicitly describe the following structured sections:
   - **Disease/Pest Diagnosis**: Identified issue or pest name.
   - **Actionable Treatments & Pesticide Recommendations**: Step-by-step chemical or organic control measures from the tool.
   - **Irrigation Strategy**: Both the pest-specific impact (e.g. drain water) AND general irrigation guidelines for the crop.
   - **Soil & Fertilizer Advice**: Recommended soil type and the specific NPK fertilizer dosage/schedule.
   - **Agronomic Windows**: Exact sowing and harvesting timelines.
   - **Recommended Varieties**: The list of validated seed varieties from ICAR.
   - **Yield Expectancy**: Estimated yield in quintals per hectare.
   - **ICAR Citation Code**: Citing the reference code (e.g. ICAR-IIHR/TOM-2023-001).
4. NEVER make up advice — only use data from the tool.
5. If no data found, say: "No ICAR-validated advisory available. Please contact your nearest Krishi Vigyan Kendra (KVK)."
6. ALWAYS respond in the SAME LANGUAGE the farmer used (e.g., Hindi, Kannada, Telugu, Marathi, or English).
7. Use respectful, culturally appropriate tone (address as "किसान भाई" in Hindi, "రైతు సోదరులారా" in Telugu, "ರೈತ ಬಾಂಧವರೇ" in Kannada, etc.).
""",
    tools=[get_crop_advisory],
)
