import json
from pathlib import Path
from typing import Dict, Any, List

async def check_scheme_eligibility(
    land_holding_hectares: float,
    annual_income_rupees: int,
    age: int,
    state: str,
    is_sc_st: bool = False,
    is_disability: bool = False,
    is_income_tax_payer: bool = False
) -> Dict[str, Any]:
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
    rules_path = Path(__file__).parent.parent.parent / "data" / "scheme_rules.json"
    
    fallback_output = {
        "eligible_schemes": [],
        "ineligible_schemes": [],
        "total_annual_benefit_rupees": 0
    }

    if not rules_path.exists():
        return fallback_output

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules_data = json.load(f)
    except Exception:
        return fallback_output

    schemes = rules_data.get("schemes", [])
    eligible_list = []
    ineligible_list = []
    total_benefit = 0

    for scheme in schemes:
        scheme_id = scheme.get("id")
        eligibility = scheme.get("eligibility_rules", {})
        
        is_eligible = True
        reasons = []

        # Check land holding limit
        max_land = eligibility.get("max_land_holding_ha")
        if max_land is not None and land_holding_hectares > max_land:
            is_eligible = False
            reasons.append(f"Land holding ({land_holding_hectares} ha) exceeds max limit of {max_land} ha.")

        # Check exclusion criteria
        excluded_groups = eligibility.get("excluded_if", [])
        if "income_tax_payer" in excluded_groups and is_income_tax_payer:
            is_eligible = False
            reasons.append("Income tax payers are excluded.")

        # Check age limits
        min_age = eligibility.get("min_age")
        max_age = eligibility.get("max_age")
        if min_age is not None and age < min_age:
            is_eligible = False
            reasons.append(f"Age {age} is below minimum age requirement of {min_age} years.")
        if max_age is not None and age > max_age:
            is_eligible = False
            reasons.append(f"Age {age} exceeds maximum age limit of {max_age} years.")

        # Check state constraints
        allowed_states = eligibility.get("states", "all")
        if allowed_states != "all" and isinstance(allowed_states, list):
            if state.lower() not in [s.lower() for s in allowed_states]:
                is_eligible = False
                reasons.append(f"Scheme not active in state '{state}'.")

        # Compile result
        res = {
            "scheme_id": scheme_id,
            "scheme_name": scheme.get("name"),
            "scheme_name_local": scheme.get("name_hi", ""),  # Fallback to Hindi name
            "annual_benefit": f"₹{scheme.get('annual_benefit_rupees', 0)}/year" if scheme.get("annual_benefit_rupees", 0) > 0 else "Varies / Subsidy-based",
            "eligible": is_eligible,
            "reason": "Meets all criteria." if is_eligible else "; ".join(reasons),
            "enrollment_steps": scheme.get("enrollment_steps", []),
            "documents_required": scheme.get("documents_required", []),
            "enrollment_url": scheme.get("enrollment_url", "")
        }

        if is_eligible:
            eligible_list.append(res)
            total_benefit += scheme.get("annual_benefit_rupees", 0)
        else:
            ineligible_list.append(res)

    return {
        "eligible_schemes": eligible_list,
        "ineligible_schemes": ineligible_list,
        "total_annual_benefit_rupees": total_benefit
    }
