# Kisan Saathi (किसान साथी) — Database Map

This document registers the schemas, attributes, and relationships of Kisan Saathi's JSON-based database files.

---

## 1. Local Database Schemas

### 1. Crop Advisory Database (`crop_advisory_kb.json`)
*   **Purpose**: Stores crop advisory records mapped by crop name and state constraint.
*   **Key Fields**:
    *   `crop` (string): Crop name identifier (e.g. `"rice"`, `"wheat"`).
    *   `state` (string): Indian state name (e.g. `"Andhra Pradesh"`, `"Punjab"`).
    *   `season` (string): Growing season (`"kharif"` or `"rabi"`).
    *   `varieties` (list of strings): Approved seed varieties.
    *   `sowing_window` (string): Optimal sowing timeline.
    *   `harvesting_window` (string): Optimal harvesting timeline.
    *   `pests` (array of objects): Diagnostic profiles containing:
        *   `name` (string): English name of the pest/disease.
        *   `name_hi` (string): Hindi translation name.
        *   `symptoms` (string): List of symptoms.
        *   `treatment` (string): Actionable control measures.
        *   `irrigation_impact` (string): Disease water adjustments.
        *   `icar_reference` (string): ICAR citation code.
    *   `soil_type` (string): Suitable soil classification.
    *   `yield_estimate_qtl_per_ha` (number): Estimated yield.
    *   `fertilizer` (string): Recommended NPK application.
    *   `irrigation` (string): General irrigation guidance.

### 2. Scheme Rules Database (`scheme_rules.json`)
*   **Purpose**: Stores eligibility rules and enrollment steps for welfare schemes.
*   **Key Fields**:
    *   `id` (string): Unique identifier (e.g. `"PM-KISAN"`, `"KCC"`).
    *   `name` (string): English name.
    *   `name_hi`, `name_kn`, `name_te`, `name_mr` (strings): Translated names.
    *   `description` (string): Scheme summary.
    *   `annual_benefit_rupees` (number): Benefit amount.
    *   `eligibility_rules` (object): Rules checklist:
        *   `max_land_holding_ha` (float or null): Land size threshold.
        *   `excluded_if` (list of strings): Excluded profiles (e.g. `"income_tax_payer"`).
        *   `min_age` & `max_age` (integers or null): Age constraints.
        *   `states` (string `"all"` or list of strings): Active regions.
    *   `enrollment_url` (string): Official portal URL.
    *   `enrollment_steps` (list of strings): Registration steps.
    *   `documents_required` (list of strings): Mandatory documents.

### 3. MSP & Coordinate References (`msp_2025_26.json`)
*   **Purpose**: Stores reference Minimum Support Prices (MSP) and lat/lon coordinate offsets.
*   **Key Fields**:
    *   `msp` (object): Maps crop keys to:
        *   `price_per_quintal` (number): Current government MSP limit.
        *   `season` (string): Rabi/Kharif.
        *   `increase_pct` (float): Increase percentage.
    *   `district_coordinates` (object): Maps district names to:
        *   `lat` (float): Central latitude coordinate.
        *   `lon` (float): Central longitude coordinate.
        *   `state` (string): Associated state name.

---

## 2. Relationships & Entity-Relation Schema

```
                  +----------------------+
                  |    FARMER PROFILE    |
                  |  (Active Session)    |
                  +----------┬-----------+
                             │
                             ├───────────────┐
            (Query Crop)     │               │ (Check Coordinates)
                             ▼               ▼
+------------------------------+   +------------------------------+
|      CROP ADVISORY KB        |   |       MSP REFERENCE          |
|  Matches: crop, state, symptoms|   |  Matches: district, state    |
+--------------┬---------------+   +──────────────┬---------------+
               │                                  │
               ▼                                  ▼
+------------------------------+   +------------------------------+
|         PESTS LIST           |   |       MANDI RATES            |
|  ICAR treatment & reference  |   |  Compares live APMC rates    |
+------------------------------+   +------------------------------+
```

*   **Farmer Profile** (Root Entity):
    *   Attributes: `session_id`, `crop`, `district`, `state`, `land_holding_hectares`, `annual_income_rupees`, `age`, `is_income_tax_payer`.
    *   *Relationship*: Matches `crop` and `state` against **Crop Advisory KB** to resolve diagnoses. Matches `state` and `district` against **MSP coordinates** to calculate local weather and APMC mandi distances.
