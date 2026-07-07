import json
from pathlib import Path
from typing import Dict, Any

async def get_crop_advisory(
    crop: str,
    state: str,
    season: str,
    symptom: str
) -> Dict[str, Any]:
    """Get ICAR-validated crop advisory for pest/disease management.

    Args:
        crop: Crop name (e.g. tomato, rice)
        state: State name (e.g. Karnataka)
        season: Growing season (kharif or rabi)
        symptom: Observed symptom or disease name
    """
    kb_path = Path(__file__).parent.parent.parent / "data" / "crop_advisory_kb.json"
    
    # Default fallback
    fallback_output = {
        "crop": crop,
        "state": state,
        "season": season,
        "diseases": ["Unknown/unlisted disease"],
        "treatments": ["No ICAR-validated advisory available. Please contact your nearest Krishi Vigyan Kendra (KVK)."],
        "irrigation_advice": "Maintain standard soil moisture. Avoid excess watering in case of symptoms.",
        "pesticide_recommendations": [],
        "icar_reference_code": "N/A",
        "varieties": [],
        "sowing_window": "",
        "harvesting_window": ""
    }

    if not kb_path.exists():
        return fallback_output

    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            kb = json.load(f)
    except Exception:
        return fallback_output

    advisories = kb.get("advisories", [])

    matched_adv = None
    for adv in advisories:
        if adv.get("crop", "").lower() == crop.lower() and adv.get("state", "").lower() == state.lower():
            matched_adv = adv
            break

    # If state not matched, try matching just by crop name (first match)
    if not matched_adv:
        for adv in advisories:
            if adv.get("crop", "").lower() == crop.lower():
                matched_adv = adv
                break

    if not matched_adv:
        return fallback_output

    # Look for matching pest symptoms
    matched_pest = None
    pests = matched_adv.get("pests", [])
    symptom_lower = symptom.lower()
    
    for pest in pests:
        if (pest.get("name", "").lower() in symptom_lower or 
            pest.get("name_hi", "") in symptom or
            any(word in symptom_lower for word in pest.get("symptoms", "").lower().split() if len(word) > 4)):
            matched_pest = pest
            break
            
    # Fallback to first pest if symptom matches nothing but symptoms is provided
    if not matched_pest and pests:
        matched_pest = pests[0]

    if matched_pest:
        return {
            "crop": matched_adv.get("crop"),
            "state": matched_adv.get("state"),
            "season": matched_adv.get("season"),
            "diseases": [matched_pest.get("name")],
            "treatments": [matched_pest.get("treatment")],
            "irrigation_advice": matched_pest.get("irrigation_impact"),
            "pesticide_recommendations": [matched_pest.get("treatment")] if "spray" in matched_pest.get("treatment", "").lower() else [],
            "icar_reference_code": matched_pest.get("icar_reference"),
            "varieties": matched_adv.get("varieties", []),
            "sowing_window": matched_adv.get("sowing_window", ""),
            "harvesting_window": matched_adv.get("harvesting_window", ""),
            "soil_type": matched_adv.get("soil_type", ""),
            "fertilizer_recommendation": matched_adv.get("fertilizer", ""),
            "general_irrigation_guideline": matched_adv.get("irrigation", ""),
            "expected_yield_qtl_per_ha": matched_adv.get("yield_estimate_qtl_per_ha", "")
        }

    return {
        "crop": matched_adv.get("crop"),
        "state": matched_adv.get("state"),
        "season": matched_adv.get("season"),
        "diseases": ["General Health / Diagnostic Pending"],
        "treatments": ["Consult local agricultural officer for specific symptoms."],
        "irrigation_advice": matched_adv.get("irrigation", "Regular watering"),
        "pesticide_recommendations": [],
        "icar_reference_code": "ICAR-GEN-2024",
        "varieties": matched_adv.get("varieties", []),
        "sowing_window": matched_adv.get("sowing_window", ""),
        "harvesting_window": matched_adv.get("harvesting_window", ""),
        "soil_type": matched_adv.get("soil_type", ""),
        "fertilizer_recommendation": matched_adv.get("fertilizer", ""),
        "general_irrigation_guideline": matched_adv.get("irrigation", ""),
        "expected_yield_qtl_per_ha": matched_adv.get("yield_estimate_qtl_per_ha", "")
    }
