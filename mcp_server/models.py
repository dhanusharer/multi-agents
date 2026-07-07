from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List

# Crop Advisory
class PestInfo(BaseModel):
    name: str = Field(..., description="English name of the pest/disease")
    name_hi: str = Field("", description="Hindi name of the pest/disease")
    symptoms: str = Field(..., description="Observed symptoms")
    treatment: str = Field(..., description="Recommended control measures/treatments")
    irrigation_impact: str = Field(..., description="How irrigation should be adjusted")
    icar_reference: str = Field(..., description="Official ICAR reference code")

class GetCropAdvisoryOutput(BaseModel):
    crop: str = Field(..., description="Crop name")
    state: str = Field(..., description="Indian state name")
    season: str = Field(..., description="Growing season")
    diseases: List[str] = Field(default_factory=list, description="List of matched diseases/pests")
    treatments: List[str] = Field(default_factory=list, description="List of treatments/solutions")
    irrigation_advice: str = Field(..., description="Overall irrigation advice")
    pesticide_recommendations: List[str] = Field(default_factory=list, description="List of approved pesticides")
    icar_reference_code: str = Field(..., description="Primary ICAR reference code or 'N/A'")
    varieties: List[str] = Field(default_factory=list, description="Recommended varieties")
    sowing_window: str = Field("", description="Optimal sowing window")
    harvesting_window: str = Field("", description="Optimal harvesting window")

# Scheme Eligibility
class SchemeResult(BaseModel):
    scheme_id: str = Field(..., description="Unique scheme identifier")
    scheme_name: str = Field(..., description="English scheme name")
    scheme_name_local: str = Field("", description="Scheme name in local language")
    annual_benefit: str = Field(..., description="Summary of annual benefit")
    eligible: bool = Field(..., description="Whether the farmer is eligible")
    reason: str = Field(..., description="Detailed reason for eligibility or exclusion")
    enrollment_steps: List[str] = Field(default_factory=list, description="Step-by-step application guide")
    documents_required: List[str] = Field(default_factory=list, description="Required documents")
    enrollment_url: str = Field("", description="Official website URL")

class CheckSchemeEligibilityOutput(BaseModel):
    eligible_schemes: List[SchemeResult] = Field(default_factory=list, description="List of eligible schemes")
    ineligible_schemes: List[SchemeResult] = Field(default_factory=list, description="List of ineligible schemes")
    total_annual_benefit_rupees: int = Field(..., description="Sum of benefits from eligible schemes")

# Weather Advisory
class DayForecast(BaseModel):
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    temp_min_c: float = Field(..., description="Minimum temperature in Celsius")
    temp_max_c: float = Field(..., description="Maximum temperature in Celsius")
    humidity_pct: float = Field(..., description="Relative humidity percentage")
    rainfall_mm: float = Field(..., description="Precipitation in millimeters")
    wind_speed_kmh: float = Field(..., description="Maximum wind speed in km/h")
    recommended_action: str = Field(..., description="Crop-specific agricultural action recommended")

class GetWeatherAdvisoryOutput(BaseModel):
    crop: str = Field(..., description="Crop name")
    location: str = Field(..., description="Location name or coordinates")
    latitude: float = Field(..., description="Location latitude")
    longitude: float = Field(..., description="Location longitude")
    forecast_7day: List[DayForecast] = Field(default_factory=list, description="7-day daily forecast and advice")
    overall_advisory: str = Field(..., description="Aggregated 7-day crop action advice")
    risk_alerts: List[str] = Field(default_factory=list, description="Weather and pest risk warnings")

# Market Price
class NearestMandi(BaseModel):
    mandi_name: str = Field(..., description="Name of the market")
    district: str = Field(..., description="District name")
    state: str = Field(..., description="State name")
    commodity: str = Field(..., description="Crop/commodity name")
    price_per_quintal: float = Field(..., description="Modal price at the mandi")
    distance_km: float = Field(..., description="Distance to mandi")

class GetMarketPriceOutput(BaseModel):
    commodity: str = Field(..., description="Crop/commodity name")
    district: str = Field(..., description="District name")
    state: str = Field(..., description="State name")
    modal_price_per_quintal: float = Field(..., description="Mandi modal price")
    min_price_per_quintal: float = Field(..., description="Mandi minimum price")
    max_price_per_quintal: float = Field(..., description="Mandi maximum price")
    msp_per_quintal: float = Field(..., description="Minimum Support Price")
    price_vs_msp: str = Field(..., description="Percentage comparison against MSP")
    recommendation: str = Field(..., description="Hold vs Sell recommendation")
    nearest_mandis: List[NearestMandi] = Field(default_factory=list, description="List of nearby markets")
    price_date: str = Field(..., description="Price publication date")
