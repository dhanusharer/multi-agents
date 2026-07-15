from __future__ import annotations
import json
import time
import re
from typing import List, Dict, Any, Optional

try:
    from google_adk import Agent  # type: ignore
except ImportError:
    try:
        from google.adk.agents import Agent  # type: ignore
    except ImportError:
        # ADK not installed — define a stub so the orchestrator still works standalone
        class Agent:
            def __init__(self, **kwargs): pass

from agents.crop_advisor import crop_advisor_agent
from agents.scheme_finder import scheme_finder_agent
from agents.weather_planner import weather_planner_agent
from agents.market_price import market_price_agent
from security.input_guard import InputGuard
from security.output_validator import OutputValidator
from security.audit_log import AuditLogger

class InMemorySessionService:
    """Simple in-memory session memory for farmer profiles."""
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def load(self, session_id: str) -> Dict[str, Any]:
        """Load farmer profile details. Returns default if not exists."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "crop": None,
                "district": None,
                "state": None,
                "language": "en",
                "land_holding_hectares": 1.0,
                "annual_income_rupees": 80000,
                "age": 40,
                "is_income_tax_payer": False
            }
        return self.sessions[session_id]

    def update(self, session_id: str, **kwargs) -> None:
        """Update farmer profile session state."""
        if session_id not in self.sessions:
            self.load(session_id)
        self.sessions[session_id].update(kwargs)

    def clear(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

# Main Prompt instructions for Orchestrator intent routing and LoopAgent missing parameter refinement.
ORCHESTRATOR_INSTRUCTION = """
You are "Kisan Saathi" (\u0915\u093f\u0938\u093e\u0928 \u0938\u093e\u0925\u0940), the central multi-agent orchestrator for Indian smallholder farmers.
You understand: Hindi, Kannada, Telugu, Marathi, and English.

YOUR ROLES:
1. DETECT LANGUAGE: Identify the input language (Hindi, Kannada, Telugu, Marathi, or English).
2. EXTRACT PARAMETERS: Find crop names, state, district, land holding, income, age, symptoms.
3. DETECT MISSING PARAMETERS: If a query needs crop or location, and you don't have them in the context, ask the farmer directly for them in their language.
4. DETECT INTENT: Decide which specialist agents to route to:
   - CROP_ADVISORY
   - SCHEME_LOOKUP
   - WEATHER_ADVICE
   - MARKET_PRICE
   - GENERAL (agricultural greetings/general info)
5. MERGE & SYNTHESIZE: Combine the specialist responses into a single, cohesive, respectful response in the farmer's native language. Keep general greetings brief, but allow detailed specialist advisories (disease controls, weather forecasts, schemes, mandi prices) to be as comprehensive, detailed, and rich as possible to provide maximum helpful value.

IMPORTANT: NEVER mix English words into Kannada/Hindi/Telugu/Marathi sentences (no English bleed). Be culturally respectful.
"""

class KisanSaathiOrchestrator:
    """Root Orchestrator wrapping the ADK Agents with safety and memory layers."""

    def __init__(self):
        # We reuse the ADK Agent configurations
        self.crop_agent = crop_advisor_agent
        self.scheme_agent = scheme_finder_agent
        self.weather_agent = weather_planner_agent
        self.market_agent = market_price_agent

        # Security & Audit
        self.input_guard = InputGuard()
        self.output_validator = OutputValidator()
        self.audit_log = AuditLogger()
        
        # Session Memory
        self.session_service = InMemorySessionService()

        # ADK Orchestrator Agent configuration
        self.root_agent = Agent(
            name="kisan_saathi_orchestrator",
            model="gemini-2.5-flash",
            description="Root orchestrator routing queries to crop, scheme, weather, and market agents.",
            instruction=ORCHESTRATOR_INSTRUCTION,
            sub_agents=[
                self.crop_agent,
                self.scheme_agent,
                self.weather_agent,
                self.market_agent
            ]
        )

    async def detect_language_and_intent(self, query: str) -> tuple[str, List[str]]:
        """Identify query language and classify intent using the LLM model."""
        lower_q = query.lower()
        intents = []
        
        # 1. Intent Classification Keywords
        crop_keywords = [
            "\u0930\u094b\u0917", "\u092c\u0940\u092e\u093e\u0930\u0940", "\u0915\u0940\u091f", "\u0926\u0935\u093e", "pest", "disease", "treatment", "symptom", "leaves", "\u092a\u0924\u094d\u0924\u0940", "\u092a\u0940\u0932\u0940", "yellow",
            "variety", "cultivation", "grow", "planting", "advisory", "irrigation", "fertilizer", "soil", "spacing", "seed",
            "fungicide", "pesticide", "insecticide", "infestation", "blight", "rot", "borer", "bug", "spot", "\u092c\u094b\u0928\u093e", "\u092c\u0941\u0935\u093e\u0908",
            "\u092a\u0948\u0926\u093e\u0935\u093e\u0930", "\u0916\u0947\u0924\u0940", "\u092e\u093f\u091f\u094d\u091f\u0940", "\u0916\u093e\u0926", "\u091b\u093f\u0921\u093c\u0915\u093e\u0935", "\u0938\u093f\u0902\u091a\u093e\u0908", "advisory", "kheti", "buwai", "kisam", "unnat", "sowing",
            "growing", "intercropping", "guide", "plantation", "ugaye", "ugayein", "yield", "techniques", "care"
        ]
        
        scheme_keywords = [
            "\u092f\u094b\u091c\u0928\u093e", "\u0938\u092c\u094d\u0938\u093f\u0921\u0940", "\u092a\u0947\u0902\u0936\u0928", "\u0938\u0930\u0915\u093e\u0930\u0940", "scheme", "subsidy", "pension", "pm-kisan", "pmfby", "kcc", "pm kisan",
            "solar pump", "cold storage", "refinance", "insurance", "bima", "\u090b\u0923", "\u0932\u094b\u0928", "\u092a\u093e\u0924\u094d\u0930", "\u0906\u0935\u0947\u0926\u0928", "\u092a\u0902\u091c\u0940\u0915\u0930\u0923", 
            "\u0926\u0938\u094d\u0924\u093e\u0935\u0947\u091c", "\u0915\u093e\u0930\u094d\u0921", "yojana", "sarkari", "loan", "apply", "register", "paisa", "rupay", "milta", "milti", 
            "eligible", "benefits", "registration", "fpo", "financing", "nabard", "shc", "soil health card"
        ]
        
        weather_keywords = [
            "\u092e\u094c\u0938\u092e", "\u092c\u093e\u0930\u093f\u0936", "\u0924\u093e\u092a\u092e\u093e\u0928", "\u0939\u0935\u093e", "weather", "rain", "temperature", "forecast", "forecasts", "climate", "wheather", "precipitation", "wind", 
            "humidity", "hail", "frost", "cyclone", "monsoon", "cloud", "fog", "heatwave", "\u092a\u0942\u0930\u094d\u0935\u093e\u0928\u0941\u092e\u093e\u0928", "\u0915\u094b\u0939\u0930\u093e", "\u092a\u093e\u0932\u093e", 
            "\u0913\u0932\u0947", "\u0924\u0942\u095e\u093e\u0928", "\u0917\u0930\u094d\u092e\u0940", "barish", "baarish", "temp", "hailstorm", "dry spell", "wind speed", "lightning", 
            "uv index", "dew point", "aandhi"
        ]
        
        market_keywords = [
            "\u092d\u093e\u0935", "\u0915\u0940\u092e\u0924", "\u0926\u093e\u092e", "\u092e\u0902\u0921\u0940", "\u0926\u0930", "msp", "price", "prices", "mandi", "rate", "rates", "market", "\u092c\u0947\u091a\u0947", "\u092c\u093f\u0915", "bhav", "kimat", 
            "dam", "sell", "hold", "cost", "worth"
        ]
        
        if any(w in lower_q for w in crop_keywords):
            intents.append("CROP_ADVISORY")
        if any(w in lower_q for w in scheme_keywords):
            intents.append("SCHEME_LOOKUP")
        if any(w in lower_q for w in weather_keywords):
            intents.append("WEATHER_ADVICE")
        if any(w in lower_q for w in market_keywords):
            intents.append("MARKET_PRICE")

        if not intents:
            intents.append("GENERAL")

        # 2. Language Detection
        language = "en"
        # Indian native scripts check
        if re.search(r"[\u0900-\u097F]", query):
            # Devanagari script (Hindi/Marathi)
            if any(w in query for w in ["\u0906\u0939\u0947", "\u0915\u0930\u0942", "\u0938\u093e\u0902\u0917\u093e", "\u092e\u093e\u0939\u093f\u0924\u0940", "\u092f\u0947\u0908\u0932", "\u0915\u093e\u0922\u093e", "\u092a\u093e\u0939\u093f\u091c\u0947"]):
                language = "mr"
            else:
                language = "hi"
        elif re.search(r"[\u0C80-\u0CFF]", query):
            language = "kn"
        elif re.search(r"[\u0C00-\u0C7F]", query):
            language = "te"
        else:
            # Transliteration check (Hinglish/Romanized Hindi)
            hinglish_words = {
                "mere", "gaon", "mein", "gehun", "gehu", "ke", "liye", "koi", "sarkari", "yojana", "hai", "kya", 
                "kal", "baarish", "barish", "hogi", "hoon", "aur", "laga", "raha", "paisa", "kab", "aayega", 
                "batao", "buwai", "karein", "kaise", "chal", "khet", "beej", "aandhi", "aane", "sambhavna", 
                "dhanyavaad", "dhanyavad", "bahut", "madad", "chahiye", "apni", "fasal", "baare", "ka", "ki", 
                "ko", "se", "nahi", "ugaye", "ugayein", "bima", "unnat", "tel", "bik", "karun", "aapne", "kis",
                "kaun", "si", "milta", "milti", "sahi", "samay", "kheti"
            }
            words = set(re.findall(r"\b\w+\b", lower_q))
            if words.intersection(hinglish_words):
                language = "hi"

        # Fallback to semantic LLM classification if keyword classification defaults to GENERAL
        if intents == ["GENERAL"]:
            try:
                import os
                from google import genai
                from google.genai import types
                
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    You are the Kisan Saathi intent classifier.
                    Analyze the following query from an Indian farmer:
                    "{query}"
                    
                    Classify the query into one or more of these intents:
                    - CROP_ADVISORY: queries about crop diseases, pests, treatments, soil, sowing, varieties, seeds, irrigation, fertilizers.
                    - SCHEME_LOOKUP: queries about government schemes, subsidies, loans, bima/insurance, pension, eligibility.
                    - WEATHER_ADVICE: queries about weather, rain, temperature, wind, forecast, climate, or weather actions.
                    - MARKET_PRICE: queries about mandi prices, crop rates, market value, MSP comparisons.
                    - GENERAL: greetings, generic thanks, or off-topic queries.
                    
                    Identify the query language (en, hi, kn, te, mr).
                    
                    Respond ONLY with a valid JSON block containing:
                    {{
                        "intents": ["INTENT_NAME_1", ...],
                        "language": "lang_code"
                    }}
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    if response.text:
                        res_data = json.loads(response.text.strip())
                        llm_intents = res_data.get("intents", [])
                        llm_lang = res_data.get("language", "en")
                        
                        valid_intents = [i for i in llm_intents if i in ["CROP_ADVISORY", "SCHEME_LOOKUP", "WEATHER_ADVICE", "MARKET_PRICE"]]
                        if valid_intents:
                            intents = valid_intents
                        if llm_lang in ["en", "hi", "kn", "te", "mr"]:
                            language = llm_lang
            except Exception:
                pass
                
        return language, intents

    async def extract_parameters(self, query: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract crop, location, and other farming details from query."""
        lower_q = query.lower()
        extracted = {}

        # 1. Comprehensive Crop Detection
        crop_mapping = {
            "rice": "rice", "paddy": "rice", "\u0927\u093e\u0928": "rice", "\u091a\u093e\u0935\u0932": "rice", "\u092d\u093e\u0924": "rice", "\u0CAD\u0CA4\u0CCD\u0CA4": "rice", "\u0C35\u0C30\u0C3F": "rice",
            "wheat": "wheat", "gehun": "wheat", "gehu": "wheat", "\u0917\u0947\u0939\u0942\u0902": "wheat", "\u0917\u0939\u0942": "wheat", "\u0C97\u0CCB\u0CA7\u0CBF": "wheat", "\u0C17\u0C4B\u0C27\u0C41\u0C2E": "wheat",
            "soybean": "soybean", "\u0938\u094b\u092f\u093e\u092c\u0940\u0928": "soybean",
            "mustard": "mustard", "sarson": "mustard", "\u0938\u0930\u0938\u094b\u0902": "mustard", "\u092e\u094b\u0939\u0930\u0940": "mustard", "\u0CB8\u0CBE\u0CB8\u0CBF\u0CB5\u0CC6": "mustard", "\u0C06\u0C35\u0C3E\u0C32\u0C41": "mustard",
            "cotton": "cotton", "k \u0915\u092a\u093e\u0938": "cotton", "\u0915\u093e\u092a\u0942\u0938": "cotton", "\u0CB9\u0CA4\u0CCD\u0CA4\u0CBF": "cotton", "\u0C2A\u0C24\u0C4D\u0C24\u0C3F": "cotton",
            "maize": "maize", "corn": "maize", "\u092e\u0915\u094d\u0915\u093e": "maize", "\u092e\u0915\u093e": "maize", "\u0CAE\u0CC6\u0C95\u0CCD\u0C95\u0CC6\u0C9C\u0CCB\u0CB3": "maize", "\u0C2E\u0C4A\u0C15\u0C4D\u0C15\u0C1C\u0C4A\u0C28\u0C4D\u0C28": "maize",
            "jowar": "jowar", "sorghum": "jowar", "\u091c\u094d\u0935\u093e\u0930": "jowar", "\u0C9C\u0CCB\u0CB3": "jowar", "\u0C1C\u0C4A\u0C28\u0C4D\u0C28\u0C32\u0C41": "jowar",
            "bajra": "bajra", "millet": "bajra", "pearl millet": "bajra", "\u092c\u093e\u091c\u0930\u093e": "bajra", "\u0CB8\u0C9C\u0CCD\u0C9C\u0CC6": "bajra", "\u0CB8\u0C9C\u0CCD\u0C9C\u0CB2\u0CC1": "bajra",
            "groundnut": "groundnut", "\u092e\u0942\u0902\u0917\u092b\u0932\u0940": "groundnut", "\u092d\u0941\u0908\u092e\u0942\u0917": "groundnut", "\u0C95\u0CA1\u0CB2\u0CC6\u0C95\u0CBE\u0CAF\u0CBF": "groundnut", "\u0D35\u0D47\u0D30\u0D41\u0C36\u0C28\u0C17": "groundnut",
            "tur dal": "tur_dal", "tur_dal": "tur_dal", "arhar": "tur_dal", "\u0924\u0941\u0905\u0930": "tur_dal", "\u0924\u0942\u0930": "tur_dal", "\u0CA4\u0CCA\u0C97\u0CB0\u0CBF \u0CAC\u0CC7\u0CB3\u0CC6": "tur_dal", "\u0C15\u0C02\u0C26\u0C3F\u0C2A\u0C2A\u0C4D\u0C2A\u0C41": "tur_dal",
            "moong dal": "moong_dal", "moong_dal": "moong_dal", "\u092e\u0942\u0902\u0917": "moong_dal", "\u092e\u0942\u0917": "moong_dal", "\u0CB9\u0CC6\u0CB8\u0CB0\u0CC1 \u0CAC\u0CC7\u0CB3\u0CC6": "moong_dal", "\u0C2A\u0C46\u0C38\u0C30\u0C2A\u0C2A\u0C4D\u0C2A\u0C41": "moong_dal",
            "urad dal": "urad_dal", "urad_dal": "urad_dal", "\u0909\u0921\u093c\u0926": "urad_dal", "\u0909\u0921\u0940\u0926": "urad_dal", "\u0C89\u0CA6\u0CCD\u0CA6\u0CBF\u0CA8 \u0CAC\u0CC7\u0CB3\u0CC6": "urad_dal", "\u0C2E\u0C3F\u0C28\u0C2A\u0C2A\u0C4D\u0C2A\u0C41": "urad_dal",
            "chana": "chana", "chickpea": "chana", "\u091a\u0928\u093e": "chana", "\u0939\u0930\u092d\u0930\u093e": "chana", "\u0C95\u0CA1\u0CB2\u0CC6": "chana", "\u0C36\u0C28\u0C17\u0C32\u0C41": "chana",
            "masoor": "masoor", "lentil": "masoor", "\u092e\u0938\u0942\u0930": "masoor", "\u092e\u0938\u0941\u0930": "masoor", "\u0CAE\u0CB8\u0CC2\u0CB0\u0CCD": "masoor", "\u0C2E\u0C38\u0C42\u0C30\u0C4D": "masoor",
            "barley": "barley", "\u091c\u094c": "barley", "\u0C9C\u0CB5\u0CC6\u0C97\u0CCB\u0CA7\u0CBF": "barley", "\u0CAC\u0CBE\u0CB0\u0CCD\u0CB2\u0CC0": "barley",
            "sunflower": "sunflower", "\u0938\u0942\u0930\u091c\u092e\u0941\u0916\u0940": "sunflower", "\u0938\u0942\u0930\u094d\u092f\u092b\u0942\u0932": "sunflower", "\u0CB8\u0CC2\u0CB0\u0CCD\u0CAF\u0C95\u0CBE\u0C82\u0CA4\u0CBF": "sunflower", "\u0C2A\u0CCA\u0CA6\u0CCD\u0CA6\u0CC1\u0CA4\u0CBF\u0CB0\u0CC1\u0C97\u0CC1\u0CA1\u0CC1": "sunflower",
            "sesamum": "sesamum", "til": "sesamum", "\u0924\u093f\u0932": "sesamum", "\u0924\u0940\u0933": "sesamum", "\u0C8E\u0CB3\u0CCD\u0CB3\u0CC1": "sesamum", "nuvvalu": "sesamum", "\u0C28\u0C41\u0C35\u0C4D\u0C35\u0C41\u0C32\u0C41": "sesamum",
            "tomato": "tomato", "tamatar": "tomato", "\u091f\u092e\u093e\u091f\u0930": "tomato", "\u091f\u094b\u092e\u0945\u091f\u094b": "tomato", "\u0C9F\u0CCA\u0CAE\u0CC6\u0C9F\u0CCA": "tomato", "\u0C1F\u0C2E\u0C4B\u0C1F\u0C3E": "tomato",
            "potato": "potato", "aloo": "potato", "\u0906\u0932\u0942": "potato", "\u092c\u091f\u093e\u091f\u093e": "potato", "\u0C86\u0CB2\u0CC2\u0C97\u0CA1\u0CCD\u0CA1\u0CC6": "potato", "\u0C2C\u0C02\u0C17\u0C3E\u0C33\u0C26\u0C41\u0C02\u0C2A": "potato",
            "onion": "onion", "pyaj": "onion", "\u092a\u094d\u092f\u093e\u091c": "onion", "\u0915\u093e\u0902\u0926\u093e": "onion", "\u0C88\u0CB0\u0CC1\u0CB3\u0CCD\u0CB3\u0CBF": "onion", "\u0C09\u0C32\u0C4D\u0C32\u0C3F\u0C2A\u0C3E\u0C2F": "onion", "\u0C09\u0C32\u0C4D\u0C32\u0C3F": "onion",
            "sugarcane": "sugarcane", "ganna": "sugarcane", "\u0917\u0928\u094d\u0928\u093e": "sugarcane", "\u090a\u0938": "sugarcane", "\u0C95\u0CAC\u0CCD\u0CAC\u0CC1": "sugarcane", "\u0C1A\u0C46\u0C30\u0C15\u0C41": "sugarcane",
            "banana": "banana", "kela": "banana", "\u0915\u0947\u0932\u093e": "banana", "\u0915\u0947\u0933\u0940": "banana", "\u0CAC\u0CBE\u0CB3\u0CC6\u0CB9\u0CA3\u0CCD\u0CA3\u0CC1": "banana", "\u0C05\u0C30\u0C1F\u0C3F\u0C2A\u0C02\u0C21\u0C41": "banana",
            "mango": "mango", "aam": "mango", "\u0906\u092e": "mango", "\u0906\u0902\u092c\u093e": "mango", "\u0CAE\u0CBE\u0CB5\u0CBF\u0CA8\u0CB9\u0CA3\u0CCD\u0CA3\u0CC1": "mango", "\u0C2E\u0C3E\u0C2E\u0C3F\u0C21\u0C3F\u0C2A\u0C02\u0C21\u0C41": "mango",
            "chilli": "chilli", "mirch": "chilli", "\u092e\u093f\u0930\u094d\u091a": "chilli", "\u092e\u093f\u0930\u091a\u0940": "chilli", "\u0CAE\u0CC6\u0CA3\u0CB8\u0CBF\u0CA8\u0C95\u0CBE\u0CAF\u0CBF": "chilli", "\u0C2E\u0C3F\u0C30\u0C2A\u0C15\u0C3E\u0C2F": "chilli",
            "turmeric": "turmeric", "haldi": "turmeric", "\u0939\u0932\u094d\u0926\u0940": "turmeric", "\u0939\u0933\u0926": "turmeric", "\u0C85\u0CB0\u0CBF\u0CB6\u0CBF\u0CA8": "turmeric", "\u0C2A\u0C38\u0C41\u0C2A\u0C41": "turmeric",
            "cumin": "cumin", "jeera": "cumin", "\u091c\u0940\u0930\u093e": "cumin", "\u091c\u093f\u0930\u0947": "cumin", "\u0C9C\u0CC0\u0CB0\u0CBF\u0C97\u0CC6": "cumin", "\u0C1C\u0C40\u0C32\u0C15\u0C30\u0C4D\u0C30": "cumin",
            "garlic": "garlic", "lahsun": "garlic", "\u0932\u0939\u0938\u0941\u0928": "garlic", "\u0932\u0938\u0942\u0923": "garlic", "\u0CAC\u0CC6\u0CB3\u0CCD\u0CB3\u0CC1\u0CB3\u0CCD\u0CB3\u0CBF": "garlic", "\u0C35\u0C46\u0C32\u0C4D\u0C32\u0C41\u0C32\u0C4D\u0C32\u0C3F": "garlic",
            "apple": "apple", "seb": "apple", "\u0938\u0947\u092c": "apple", "\u0938\u092b\u0930\u091a\u0902\u0926": "apple", "\u0CB8\u0CC7\u0CAC\u0CC1": "apple", "\u0C06\u0C2A\u0C3F\u0C32\u0C4D": "apple",
            "strawberry": "strawberry", "\u0938\u094d\u091f\u094d\u0930\u0949\u092c\u0947\u0930\u0940": "strawberry",
            "coconut": "coconut", "nariyal": "coconut", "\u0928\u093e\u0930\u093f\u092f\u0932": "coconut", "\u0928\u093e\u0930\u0933": "coconut", "\u0CA4\u0CC6\u0C82\u0C97\u0CBF\u0CA8\u0C95\u0CBE\u0CAF\u0CBF": "coconut", "\u0C15\u0C4A\u0C2C\u0C4D\u0C2C\u0C30\u0C3F\u0C15\u0C3E\u0C2F": "coconut",
            "tea": "tea", "chai": "tea", "\u091a\u093e\u092f": "tea", "\u091a\u0939\u093e": "tea", "\u0C9A\u0CB9\u0CBE": "tea", "\u0C1F\u0C40": "tea",
            "cashew": "cashew", "kaju": "cashew", "\u0915\u093e\u091c\u0942": "cashew", "\u0C97\u0CC7\u0CB0\u0CC1\u0CAC\u0CC0\u0C9C": "cashew", "\u0C1C\u0C40\u0C21\u0C3F\u0C2A\u0C2A\u0C4D\u0C2A\u0C41": "cashew",
            "rubber": "rubber", "\u0930\u092c\u0930": "rubber", "\u0CB0\u0CAC\u0CCD\u0CAC\u0CB0\u0CCD": "rubber", "\u0CB0\u0CAC\u0CCD\u0CAC\u0CB0\u0CC1": "rubber",
            "coffee": "coffee", "\u0915\u0949\u092b\u0940": "coffee", "\u0C95\u0CBE\u0CAB\u0CBF": "coffee", "\u0C15\u0C3E\u0C2B\u0C40": "coffee",
            "pepper": "pepper", "black pepper": "pepper", "\u0915\u093e\u0932\u0940 \u092e\u093f\u0930\u094d\u091a": "pepper", "\u0915\u093e\u0933\u0940 \u092e\u093f\u0930\u0940": "pepper", "\u0C95\u0CBE\u0CB3\u0CC1\u0CAE\u0CC6\u0CA3\u0CB8\u0CC1": "pepper", "\u0C2E\u0C3F\u0C30\u0C3F\u0C2F\u0C3E\u0C32\u0C41": "pepper",
            "cardamom": "cardamom", "elaichi": "cardamom", "\u0907\u0932\u093e\u092f\u091a\u0940": "cardamom", "\u0935\u0947\u0932\u091a\u0940": "cardamom", "\u0C8F\u0CB2\u0C95\u0CCD\u0C95\u0CBF": "cardamom", "\u0C35\u0C46\u0C32\u0C15\u0C41\u0C32\u0C41": "cardamom",
            "dragon fruit": "dragon fruit", "\u0921\u094d\u0930\u0945\u0917\u0928 \u092b\u094d\u0930\u0942\u091f": "dragon fruit",
            "millets": "millets", "millet": "millets", "\u0930\u093e\u0917\u0940": "millets", "ragi": "millets"
        }
        
        for crop_key in sorted(crop_mapping.keys(), key=len, reverse=True):
            if crop_key in lower_q:
                extracted["crop"] = crop_mapping[crop_key]
                break

        # 2. Comprehensive District/State Detection
        location_mapping = {
            "indore": ("indore", "madhya pradesh"),
            "nashik": ("nashik", "maharashtra"),
            "jaipur": ("jaipur", "rajasthan"),
            "lucknow": ("lucknow", "uttar pradesh"),
            "latur": ("latur", "maharashtra"),
            "karnal": ("karnal", "haryana"),
            "raipur": ("raipur", "chhattisgarh"),
            "erode": ("erode", "tamil nadu"),
            "agra": ("agra", "uttar pradesh"),
            "bhubaneswar": ("bhubaneswar", "odisha"),
            "bellary": ("bellary", "karnataka"),
            "unjha": ("unjha", "gujarat"),
            "mandsaur": ("mandsaur", "madhya pradesh"),
            "amritsar": ("amritsar", "punjab"),
            "kolhapur": ("kolhapur", "maharashtra"),
            "mahabaleshwar": ("mahabaleshwar", "maharashtra"),
            "shimla": ("shimla", "himachal pradesh"),
            "pune": ("pune", "maharashtra"),
            "ratnagiri": ("ratnagiri", "maharashtra"),
            "coorg": ("coorg", "karnataka"),
            "kochi": ("kochi", "kerala"),
            "varanasi": ("varanasi", "uttar pradesh"),
            "kottayam": ("kottayam", "kerala"),
            "jodhpur": ("jodhpur", "rajasthan"),
            "kodagu": ("kodagu", "karnataka"),
            "coorg": ("kodagu", "karnataka"),
            "solan": ("solan", "himachal pradesh"),
            "mangalore": ("mangalore", "karnataka"),
            "tumkur": ("tumkur", "karnataka"),
            "kolar": ("kolar", "karnataka"),
            "mandya": ("mandya", "karnataka"),
            "shimoga": ("shimoga", "karnataka"),
            "ludhiana": ("ludhiana", "punjab"),
            "guntur": ("guntur", "andhra pradesh"),
            "nellore": ("nellore", "andhra pradesh"),
            "vidarbha": ("vidarbha", "maharashtra"),
            "haryana": ("", "haryana"),
            "rajasthan": ("", "rajasthan"),
            "punjab": ("", "punjab"),
            "gujarat": ("", "gujarat"),
            "kerala": ("", "kerala"),
            "telangana": ("", "telangana"),
            "odisha": ("", "odisha"),
            "bihar": ("", "bihar"),
            "himachal pradesh": ("", "himachal pradesh"),
            "madhya pradesh": ("", "madhya pradesh"),
            "mp": ("", "madhya pradesh"),
            "uttar pradesh": ("", "uttar pradesh"),
            "up": ("", "uttar pradesh"),
            "andhra pradesh": ("", "andhra pradesh"),
            "ap": ("", "andhra pradesh"),
            "karnataka": ("", "karnataka"),
            "maharashtra": ("", "maharashtra"),
            "tamil nadu": ("", "tamil nadu"),
            "west bengal": ("", "west bengal")
        }

        for loc_key in sorted(location_mapping.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(loc_key)}\b"
            if re.search(pattern, lower_q):
                dist, st = location_mapping[loc_key]
                if dist:
                    extracted["district"] = dist
                if st:
                    extracted["state"] = st.capitalize()
                break

        # 3. Land holding extraction
        land_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectare|hektar|ha|acre|\u090f\u0915\u0930|\u0CB5\u0CBF\u0C98\u0CBE|bigha| \u091c\u092e\u0940\u0928| \u092d\u0942\u092e\u093f)", lower_q)
        if land_match:
            val = float(land_match.group(1))
            if "acre" in lower_q or "\u090f\u0915\u0930" in lower_q:
                extracted["land_holding_hectares"] = round(val / 2.47, 2)
            else:
                extracted["land_holding_hectares"] = val

        # Merge with existing session profile
        profile.update({k: v for k, v in extracted.items() if v is not None})
        return profile

    async def run(self, query: str, session_id: str = "default_session", image_base64: Optional[str] = None) -> str:
        """Process farmer query through validation, dispatch, synthesis, and safety checks."""
        start_time = time.time()
        
        # 1. Input Guard Safety check
        is_safe, error_reason = self.input_guard.validate_query(query)
        if not is_safe:
            self.audit_log.log_security_event(session_id, "input_injection", error_reason or "Injection detected", True)
            # Check query language to return proper localized block message
            lang, _ = await self.detect_language_and_intent(query)
            return self.output_validator.get_safe_error_message(lang)
            
        # 2. Session memory load
        profile = self.session_service.load(session_id)
        
        # 3. Detect Language & Intent
        language, intents = await self.detect_language_and_intent(query)

        # AI Vision Multimodal Analysis:
        self.vision_prefix = ""
        if image_base64:
            import os
            import base64
            from google import genai
            from google.genai import types

            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                try:
                    client = genai.Client(api_key=api_key)
                    # Parse base64
                    mime_type = "image/jpeg"
                    image_data = image_base64
                    if "," in image_base64:
                        header, image_data = image_base64.split(",", 1)
                        if "image/png" in header:
                            mime_type = "image/png"
                        elif "image/webp" in header:
                            mime_type = "image/webp"
                            
                    raw_bytes = base64.b64decode(image_data)
                    image_part = types.Part.from_bytes(
                        data=raw_bytes,
                        mime_type=mime_type
                    )
                    
                    prompt = """
                    You are an expert plant pathologist. Analyze this crop leaf photo.
                    Identify:
                    1. The name of the crop (must be one of: tomato, rice, wheat, cotton, maize, sugarcane, potato, onion, soybean, banana, mango, chilli, turmeric, mustard, lentil, chickpea, sunflower, jute, tea).
                    2. The disease or pest symptoms visible in the photo.
                    
                    Respond ONLY with a valid JSON block containing:
                    {
                        "crop": "crop_name",
                        "detected_disease": "disease_or_pest_name",
                        "symptoms": "short symptom description",
                        "confidence": 0.95
                    }
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[image_part, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    
                    if response.text:
                        res_data = json.loads(response.text.strip())
                        detected_crop = res_data.get("crop", "").lower()
                        detected_disease = res_data.get("detected_disease", "")
                        
                        # Update session details with detected crop
                        valid_crops = ["tomato", "rice", "wheat", "cotton", "maize", "sugarcane", "potato", "onion", "soybean", "banana", "mango", "chilli", "turmeric", "mustard", "lentil", "chickpea", "sunflower", "jute", "tea"]
                        if detected_crop in valid_crops:
                            profile["crop"] = detected_crop
                            self.session_service.update(session_id, **profile)
                            
                        # Set symptoms for tool lookup
                        query = detected_disease or query
                        if "CROP_ADVISORY" not in intents:
                            intents.append("CROP_ADVISORY")
                            
                        # Add dynamic visual diagnosis header
                        if language == "hi":
                            self.vision_prefix = f"📷 **[एआई छवि निदान]**: मैंने आपके द्वारा अपलोड की गई तस्वीर का विश्लेषण किया।\n• पहचाना गया पौधा: **{detected_crop.capitalize()}**\n• संभावित रोग/कीट: **{detected_disease}**\n\n"
                        elif language == "kn":
                            self.vision_prefix = f"📷 **[AI ಚಿತ್ರ ವಿಶ್ಲೇಷಣೆ]**: ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಚಿತ್ರವನ್ನು ವಿಶ್ಲೇಷಿಸಲಾಗಿದೆ.\n• ಗುರುತಿಸಲಾದ ಬೆಳೆ: **{detected_crop.capitalize()}**\n• ಸಂಭವನೀಯ ರೋಗ/ಕೀಟ: **{detected_disease}**\n\n"
                        elif language == "te":
                            self.vision_prefix = f"📷 **[AI చిత్ర విశ్లేషణ]**: మీరు అప్ లోడ్ చేసిన చిత్రాన్ని విశ్లేషించాను.\n• గుర్తించిన పంట: **{detected_crop.capitalize()}**\n• ఆశించిన తెగులు/కీటకం: **{detected_disease}**\n\n"
                        elif language == "mr":
                            self.vision_prefix = f"📷 **[AI प्रतिमा विश्लेषण]**: मी अपलोड केलेल्या प्रतिमेचे विश्लेषण केले.\n• पिकाचे नाव: **{detected_crop.capitalize()}**\n• संभाव्य रोग/कीट: **{detected_disease}**\n\n"
                        else:
                            self.vision_prefix = f"📷 **[AI Image Diagnosis]**: I analyzed the uploaded photo.\n• Crop Identified: **{detected_crop.capitalize()}**\n• Suspected Disease/Pest: **{detected_disease}**\n\n"
                except Exception as e:
                    self.vision_prefix = f"⚠️ [AI Vision Error]: Failed to analyze image. {str(e)}\n\n"

        # Restore pending intents if the current intent is GENERAL and we have a loop pending
        if "GENERAL" in intents and profile.get("pending_intents"):
            intents = profile.get("pending_intents")
            profile["pending_intents"] = None

        self.audit_log.log_query(session_id, "orchestrator", query, language, ", ".join(intents))

        # 4. Extract parameters & update profile
        profile = await self.extract_parameters(query, profile)
        self.session_service.update(session_id, **profile)

        # LoopAgent missing parameter refinement:
        # If crop is missing for CROP_ADVISORY or MARKET_PRICE, ask for it
        if "CROP_ADVISORY" in intents or "MARKET_PRICE" in intents:
            if not profile.get("crop"):
                missing_msg = {
                    "hi": "कृपया अपनी फसल का नाम बताएं (जैसे: टमाटर, गेहूं, धान)।",
                    "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಬೆಳೆಯ ಹೆಸರನ್ನು ತಿಳಿಸಿ (ಉದಾಹರಣೆಗೆ: ಟೊಮೆಟೊ, ಭತ್ತ, ಗೋಧಿ).",
                    "te": "దయచేసి మీ పంట పేరు చెప్పండి (ఉదాహరణకు: టమోటా, వరి, గోధుమ).",
                    "mr": "कृपया तुमच्या पिकाचे नाव सांगा (जसे की: टोमॅटो, गहू, भात).",
                    "en": "Please tell me the name of your crop (e.g., tomato, rice, wheat)."
                }
                profile["pending_intents"] = intents
                self.session_service.update(session_id, **profile)
                return missing_msg.get(language, missing_msg["en"])

        # If location is missing for WEATHER_ADVICE or MARKET_PRICE, ask for it
        if "WEATHER_ADVICE" in intents or "MARKET_PRICE" in intents:
            if not profile.get("district") and not profile.get("state"):
                missing_msg = {
                    "hi": "कृपया अपने जिले या राज्य का नाम बताएं ताकि मैं सही जानकारी दे सकूं।",
                    "kn": "ನಿಮಗೆ ಸರಿಯಾದ ಮಾಹಿತಿ ನೀಡಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ ಜಿಲ್ಲೆ ಅಥವಾ राज्यದ ಹೆಸರನ್ನು ತಿಳಿಸಿ.",
                    "te": "మీకు సరైన సమాచారం అందించడానికి దయచేసి మీ జిల్లా లేదా రాష్ట్రం పేరు చెప్పండి.",
                    "mr": "कृपया तुमच्या जिल्ह्याचे किंवा राज्याचे नाव सांगा जेणेकरून मी अचूक माहिती देऊ शकेन.",
                    "en": "Please provide your district or state name so I can fetch the correct details."
                }
                profile["pending_intents"] = intents
                self.session_service.update(session_id, **profile)
                return missing_msg.get(language, missing_msg["en"])

        # 5. Delegate to specialist agents
        agent_responses = {}
        
        # Map parameters for tools
        crop = profile.get("crop", "wheat")
        state = profile.get("state") or "Punjab"
        district = profile.get("district") or "amritsar"
        
        # Coordinates mapping lookup from district
        from pathlib import Path
        latitude, longitude = 20.0, 77.0 # Default center of India
        
        # Load from msp_2025_26.json if available
        msp_path = Path(__file__).parent.parent / "data" / "msp_2025_26.json"
        coords = {}
        if msp_path.exists():
            try:
                with open(msp_path, "r", encoding="utf-8") as f:
                    msp_data = json.load(f)
                coords = msp_data.get("district_coordinates", {})
            except Exception:
                pass
                
        if district and district.lower() in coords:
            latitude = coords[district.lower()]["lat"]
            longitude = coords[district.lower()]["lon"]
            if not state:
                state = coords[district.lower()]["state"]
        
        # Fallback to state central coordinates if district coordinates not matched or missing
        state_coords = {
            "karnataka": (13.34, 77.10),
            "maharashtra": (18.52, 73.85),
            "punjab": (31.63, 74.87),
            "uttar pradesh": (26.84, 80.94),
            "andhra pradesh": (16.30, 80.43),
            "telangana": (17.38, 78.48),
            "rajasthan": (26.91, 75.78),
            "gujarat": (23.02, 72.57),
            "kerala": (9.93, 76.26),
            "bihar": (25.59, 85.13),
            "himachal pradesh": (31.10, 77.17),
            "madhya pradesh": (22.71, 75.85),
            "haryana": (29.68, 76.99),
            "odisha": (20.29, 85.82),
            "west bengal": (22.57, 88.36),
            "chhattisgarh": (21.25, 81.63),
            "tamil nadu": (11.34, 77.71)
        }
        
        if state and (latitude == 20.0 and longitude == 77.0 or not district):
            st_key = state.lower()
            if st_key in state_coords:
                latitude, longitude = state_coords[st_key]

        # Call agents via tool implementations from server wrapper to enable full audit logging & validation
        if "CROP_ADVISORY" in intents:
            from mcp_server.kisan_mcp_server import get_crop_advisory_tool
            adv_data = await get_crop_advisory_tool(crop, state, "kharif", query, session_id=session_id)
            agent_responses["CROP_ADVISORY"] = self._format_crop_response(adv_data, language)

        if "SCHEME_LOOKUP" in intents:
            from mcp_server.kisan_mcp_server import check_scheme_eligibility_tool
            sch_data = await check_scheme_eligibility_tool(
                land_holding_hectares=profile.get("land_holding_hectares", 1.5),
                annual_income_rupees=profile.get("annual_income_rupees", 80000),
                age=profile.get("age", 45),
                state=state,
                session_id=session_id
            )
            agent_responses["SCHEME_LOOKUP"] = self._format_scheme_response(sch_data, language)

        if "WEATHER_ADVICE" in intents:
            from mcp_server.kisan_mcp_server import get_weather_advisory_tool
            weath_data = await get_weather_advisory_tool(crop, latitude, longitude, session_id=session_id)
            agent_responses["WEATHER_ADVICE"] = self._format_weather_response(weath_data, language)

        if "MARKET_PRICE" in intents:
            from mcp_server.kisan_mcp_server import get_market_price_tool
            price_data = await get_market_price_tool(crop, state, district, session_id=session_id)
            agent_responses["MARKET_PRICE"] = self._format_market_response(price_data, language)

        if "GENERAL" in intents or not agent_responses:
            general_msg = {
                "hi": "\u0928\u092e\u0938\u094d\u0924\u0947 \u0915\u093f\u0938\u093e\u0928 \u092d\u093e\u0908, \u092e\u0948\u0902 \u0915\u093f\u0938\u093e\u0928 \u0938\u093e\u0925\u0940 \u0939\u0942\u0901\u0964 \u092e\u0948\u0902 \u092b\u0938\u0932 \u0938\u0932\u093e\u0939, \u092e\u094c\u0938\u092e \u092a\u0942\u0930\u094d\u0935\u093e\u0928\u0941\u092e\u093e\u0928, \u092e\u0902\u0921\u0940 \u092d\u093e\u0935 \u0914\u0930 \u0938\u0930\u0915\u093e\u0930\u0940 \u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u0915\u0940 \u091c\u093e\u0928\u0915\u093e\u0930\u0940 \u0926\u0947 \u0938\u0915\u0924\u093e \u0939\u0942\u0901\u0964 \u0906\u092a \u092e\u0941\u091d\u0938\u0947 \u0915\u094b\u0908 \u092d\u0940 \u0915\u0943\u0937\u093f \u092a\u094d\u0930\u0936\u094d\u0928 \u092a\u0942\u091b \u0938\u0915\u0924\u0947 \u0939\u0948\u0902\u0964",
                "kn": "\u0CA8\u0CAE\u0CB8\u0CCD\u0C95\u0CBE\u0CB0 \u0CB0\u0CC8\u0CA4 \u0CAC\u0CBE\u0C82\u0CA7\u0CB5\u0CB0\u0CC7, \u0CA8\u0CBE\u0CA8\u0CC1 \u0CA8\u0CBF\u0CAE\u0CCD\u0CAE \u0C95\u0CBF\u0CB8\u0CBE\u0CA8\u0CCD \u0CB8\u0CBE\u0CA5\u0CBF. \u0CA8\u0CBE\u0CA8\u0CC1 \u0CAC\u0CC6\u0CB3\u0CC6 \u0CB8\u0CB2\u0CB9\u0CC6, \u0CB9\u0CB5\u0CBE\u0CAE\u0CBE\u0CA8 \u0CAE\u0CC1\u0CA8\u0CCD\u0CB8\u0CC2\u0C9A\u0CA8\u0CC6, \u0CAE\u0CBE\u0CB0\u0CC1\u0C95\u0C9F\u0CCD\u0C9F\u0CC6 \u0CA7\u0CBE\u0CB0\u0CA3\u0CC6 \u0CAE\u0CA4\u0CCD\u0CA4\u0CC1 \u0CB8\u0CB0\u0CCD\u0C95\u0CBE\u0CB0\u0CBF \u0CAF\u0CCB\u0C9C\u0CA8\u0CC6\u0C97\u0CB3 \u0CAC\u0C97\u0CCD\u0C97\u0CC6 \u0CAE\u0CBE\u0CB9\u0CBF\u0CA4\u0CBF \u0CA8\u0CC0\u0CA1\u0CAC\u0CB2\u0CCD\u0CB2\u0CC6.",
                "te": "\u0C28\u0C2E\u0C38\u0C4D\u0C15\u0C3E\u0C30\u0C02 \u0C30\u0C48\u0C24\u0C41 \u0C38\u0C4B\u0C26\u0C30\u0C41\u0C32\u0C3E\u0C30\u0C3E, \u0C28\u0C47\u0C28\u0C41 \u0C2E\u0C40 \u0C15\u0C3F\u0C38\u0C3E\u0C28\u0C4D \u0C38\u0C3E\u0C25\u0C3F. \u0C28\u0C47\u0C28\u0C41 \u0C2A\u0C02\u0C1F\u0C32 \u0C38\u0C32\u0C39\u0C3E\u0C32\u0C41, \u0C35\u0C3E\u0C24\u0C3E\u0C35\u0C30\u0C23 \u0C35\u0C3F\u0C35\u0C30\u0C3E\u0C32\u0C41, \u0C2E\u0C3E\u0C30\u0C4D\u0C15\u0C46\u0C1F\u0C4D \u0C27\u0C30\u0C32\u0C41 \u0C2E\u0C30\u0C3F\u0C2F\u0C41 \u0C2A\u0C4D\u0C30\u0C2D\u0C41\u0C24\u0C4D\u0C35 \u0C2A\u0C25\u0C15\u0C3E\u0C32 \u0C38\u0C2E\u0C3E\u0C1A\u0C3E\u0C30\u0C02 \u0C05\u0C02\u0C26\u0C3F\u0C02\u0C1A\u0C17\u0C32\u0C28\u0C41.",
                "mr": "\u0928\u092e\u0938\u094d\u0915\u093e\u0930 \u0936\u0947\u0924\u0915\u0930\u0940 \u092c\u0902\u0927\u0942\u0902\u0928\u094b, \u092e\u0940 \u0906\u092a\u0932\u093e \u0915\u093f\u0938\u093e\u0928 \u0938\u093e\u0925\u0940 \u0906\u0939\u0947. \u092e\u0940 \u092a\u093f\u0915\u093e\u0902\u0935\u093f\u0937\u092f\u0940 \u0938\u0932\u094d\u0932\u093e, \u0939\u0935\u093e\u092e\u093e\u0928 \u0905\u0902\u0926\u093e\u091c, \u092c\u093e\u091c\u093e\u0930\u092d\u093e\u0935 \u0906\u0923\u093f \u0938\u0930\u0915\u093e\u0930\u0940 \u092f\u094b\u091c\u0928\u093e\u0902\u091a\u0940 \u092e\u093e\u0939\u093f\u0924\u0940 \u0926\u0947\u0909 \u0936\u0915\u0924\u094b.",
                "en": "Hello farmer, I am Kisan Saathi, your digital companion. I can assist you with crop advisory, weather forecasts, market mandi prices, and government schemes. Ask me any agricultural query."
            }
            agent_responses["GENERAL"] = general_msg.get(language, general_msg["en"])

        # 6. Response Synthesis
        synthesized_text = "\n\n".join(agent_responses.values())
        if hasattr(self, "vision_prefix") and self.vision_prefix:
            synthesized_text = self.vision_prefix + synthesized_text

        # 7. Output Validator Safety check
        is_valid, violations = self.output_validator.validate(synthesized_text)
        if not is_valid:
            self.audit_log.log_security_event(session_id, "output_violation", "; ".join(violations), True)
            return self.output_validator.get_safe_error_message(language)

        latency = (time.time() - start_time) * 1000
        self.audit_log.log_response(session_id, "orchestrator", len(synthesized_text), latency, language)

        return synthesized_text

    def _format_crop_response(self, data: dict, lang: str) -> str:
        """Helper to format crop advisory localized."""
        crop_name = data.get("crop", "")
        disease = data.get("diseases", [""])[0] if data.get("diseases") else ""
        treatment = data.get("treatments", [""])[0] if data.get("treatments") else ""
        irrigation_impact = data.get("irrigation_advice", "")
        ref = data.get("icar_reference_code", "")
        varieties = ", ".join(data.get("varieties", []))
        sowing = data.get("sowing_window", "")
        harvesting = data.get("harvesting_window", "")
        soil_type = data.get("soil_type", "")
        fertilizer = data.get("fertilizer_recommendation", "")
        irrigation_gen = data.get("general_irrigation_guideline", "")
        expected_yield = data.get("expected_yield_qtl_per_ha", "")

        if lang == "hi":
            res = f"🌾 **कृषि सलाह रिपोर्ट - {crop_name.upper()}**\n\n"
            if disease and disease != "General Health / Diagnostic Pending" and disease != "Unknown/unlisted disease":
                res += f"🔍 **रोग/कीट पहचान**: {disease}\n"
                res += f"💊 **आईसीएआर अनुशंसित उपचार**: {treatment}\n"
                res += f"💧 **कीट-विशिष्ट सिंचाई सलाह**: {irrigation_impact}\n\n"
            
            res += f"🌱 **सकल फसल दिशानिर्देश और सिंचाई प्रबंधन**:\n"
            res += f"- **सकल सिंचाई दिशानिर्देश**: {irrigation_gen}\n"
            res += f"- **अनुशंसित मिट्टी प्रकार**: {soil_type}\n"
            res += f"- **उर्वरक प्रबंधन (NPK)**: {fertilizer}\n"
            res += f"- **बुवाई अवधि**: {sowing}\n"
            res += f"- **कटाई अवधि**: {harvesting}\n"
            res += f"- **उन्नत किस्में**: {varieties}\n"
            res += f"- **अनुमानित उपज**: {expected_yield} क्विंटल/हेक्टेयर\n\n"
            res += f"*(संदर्भ संख्या: {ref})*"
            return res
        elif lang == "kn":
            res = f"🌾 **ಬೆಳೆ ಸಲಹಾ ವರದಿ - {crop_name.upper()}**\n\n"
            if disease and disease != "General Health / Diagnostic Pending" and disease != "Unknown/unlisted disease":
                res += f"🔍 **ರೋಗ/ಕೀಟ ಗುರುತಿಸುವಿಕೆ**: {disease}\n"
                res += f"💊 **ಚಿಕಿತ್ಸಾ ವಿಧಾನ**: {treatment}\n"
                res += f"💧 **ಕೀಟ-ನಿರ್ದಿಷ್ಟ ನೀರಾವರಿ ಸಲಹೆ**: {irrigation_impact}\n\n"
            
            res += f"🌱 **ಬೆಳೆ ಮಾರ್ಗಸೂಚಿಗಳು ಮತ್ತು ನೀರಾವರಿ ವಿವರಗಳು**:\n"
            res += f"- **ಸಾಮಾನ್ಯ ನೀರಾವರಿ ಮಾರ್ಗಸೂಚಿ**: {irrigation_gen}\n"
            res += f"- **ಸೂಕ್ತ ಮಣ್ಣಿನ ಪ್ರಕಾರ**: {soil_type}\n"
            res += f"- **ಗೊಬ್ಬರ ಮತ್ತು ರಸಗೊಬ್ಬರ**: {fertilizer}\n"
            res += f"- **ಬಿತ್ತನೆ ಸಮಯ**: {sowing}\n"
            res += f"- **ಕೊಯ್ಲು ಸಮಯ**: {harvesting}\n"
            res += f"- **ಶಿಫಾರಸು ಮಾಡಿದ ತಳಿಗಳು**: {varieties}\n"
            res += f"- **ನಿರೀಕ್ಷಿತ ಇಳುವರಿ**: {expected_yield} ಕ್ವಿಂಟಾಲ್/ಹೆಕ್ಟೇರ್\n\n"
            res += f"*(ಆಧಾರ ಸಂಖ್ಯೆ: {ref})*"
            return res
        elif lang == "te":
            res = f"🌾 **పంట సలహా నివేదిక - {crop_name.upper()}**\n\n"
            if disease and disease != "General Health / Diagnostic Pending" and disease != "Unknown/unlisted disease":
                res += f"🔍 **తెగులు/కీటక గుర్తింపు**: {disease}\n"
                res += f"💊 **నివారణ చర్యలు**: {treatment}\n"
                res += f"💧 **కీటక-నిర్దిష్ట నీటి యాజమాన్యం**: {irrigation_impact}\n\n"
            
            res += f"🌱 **సాగు వివరాలు & నీటి యాజమాన్యం**:\n"
            res += f"- **సాధారణ నీటి యాజమాన్యం**: {irrigation_gen}\n"
            res += f"- **అనుకూలమైన నేల**: {soil_type}\n"
            res += f"- **ఎరువుల యాజమాన్యం (NPK)**: {fertilizer}\n"
            res += f"- **విత్తే సమయం**: {sowing}\n"
            res += f"- **కోత సమయం**: {harvesting}\n"
            res += f"- **సిఫార్సు చేసిన రకాలు**: {varieties}\n"
            res += f"- **ఆశించిన దిగుబడి**: {expected_yield} క్వింటాల్/హెక్టార్\n\n"
            res += f"*(ఆధారం: {ref})*"
            return res
        elif lang == "mr":
            res = f"🌾 **पीक सल्ला अहवाल - {crop_name.upper()}**\n\n"
            if disease and disease != "General Health / Diagnostic Pending" and disease != "Unknown/unlisted disease":
                res += f"🔍 **रोग/कीट ओळख**: {disease}\n"
                res += f"💊 **आयसीएआर उपचार सल्ला**: {treatment}\n"
                res += f"💧 **कीट-विशिष्ट पाण्याचे नियोजन**: {irrigation_impact}\n\n"
            
            res += f"🌱 **पीक नियोजन आणि जल व्यवस्थापन**:\n"
            res += f"- **पाण्याचे नियोजन**: {irrigation_gen}\n"
            res += f"- **योग्य माती प्रकार**: {soil_type}\n"
            res += f"- **खत व्यवस्थापन (NPK)**: {fertilizer}\n"
            res += f"- **पेरणीचा कालावधी**: {sowing}\n"
            res += f"- **काढणीचा कालावधी**: {harvesting}\n"
            res += f"- **सुधारित जाती**: {varieties}\n"
            res += f"- **संभाव्य उत्पन्न**: {expected_yield} क्विंटल/हेक्टर\n\n"
            res += f"*(संदर्भ: {ref})*"
            return res
        else:
            res = f"🌾 **Agricultural Crop Advisory Report - {crop_name.upper()}**\n\n"
            if disease and disease != "General Health / Diagnostic Pending" and disease != "Unknown/unlisted disease":
                res += f"🔍 **Disease/Pest Diagnosis**: {disease}\n"
                res += f"💊 **ICAR Validated Treatment**: {treatment}\n"
                res += f"💧 **Pest-Specific Irrigation Impact**: {irrigation_impact}\n\n"
            
            res += f"🌱 **Cultivation Details & General Irrigation Guide**:\n"
            res += f"- **General Irrigation Guideline**: {irrigation_gen}\n"
            res += f"- **Soil Recommendation**: {soil_type}\n"
            res += f"- **NPK Fertilizer Dosage**: {fertilizer}\n"
            res += f"- **Sowing Window**: {sowing}\n"
            res += f"- **Harvesting Window**: {harvesting}\n"
            res += f"- **ICAR Recommended Seed Varieties**: {varieties}\n"
            res += f"- **Expected Yield Expectancy**: {expected_yield} qtl/ha\n\n"
            res += f"*(Reference Code: {ref})*"
            return res

    def _format_scheme_response(self, data: dict, lang: str) -> str:
        """Helper to format scheme eligibility localized."""
        eligible = data.get("eligible_schemes", [])
        
        if not eligible:
            if lang == "hi": return "\u274C \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u092e\u093e\u0928\u0926\u0902\u0921\u094b\u0902 \u0915\u0947 \u0906\u0927\u093e\u0930 \u092a\u0930 \u0906\u092a \u0915\u093f\u0938\u0940 \u092d\u0940 \u092f\u094b\u091c\u0928\u093e \u0915\u0947 \u0932\u093f\u090f \u092a\u093e\u0924\u094d\u0930 \u0928\u0939\u0940\u0902 \u0939\u0948\u0902\u0964"
            elif lang == "kn": return "\u274C \u0CA8\u0CBF\u0CAE\u0CCD\u0CAE \u0CAA\u0CCD\u0CB0\u0CCA\u0CAB\u0CC8\u0CB2\u0CCD \u0C86\u0CA7\u0CBE\u0CB0\u0CA6 \u0CAE\u0CC7\u0CB2\u0CC6 \u0CAF\u0CBE\u0CB5\u0CC1\u0CA6\u0CC7 \u0CAF\u0CCB\u0C9C\u0CA8\u0CC6\u0C97\u0CC6 \u0C85\u0CB0\u0CCD\u0CB9\u0CA4\u0CC6 \u0CB9\u0CCA\u0C82\u0CA6\u0CBF\u0CB2\u0CCD\u0CB2."
            elif lang == "te": return "\u274C \u0C2E\u0C40 \u0C35\u0C3F\u0C35\u0C30\u0C3E\u0C32 \u0C2A\u0C4D\u0C30\u0C15\u0C3E\u0C30\u0C02 \u0C0F \u0C2A\u0C25\u0C15\u0C3E\u0C28\u0C3F\u0C15\u0C40 \u0C05\u0C30\u0C4D\u0C39\u0C24 \u0C32\u0C47\u0C26\u0C41."
            elif lang == "mr": return "\u274C \u0938\u0926\u094d\u092f \u0928\u093f\u0915\u0937\u093e\u0902\u0928\u0941\u0938\u093e\u0930 \u0924\u0941\u092e\u094d\u0939\u0940 \u0915\u094b\u0923\u0924\u094d\u092f\u093e\u0939\u0940 \u092f\u094b\u091c\u0928\u0947\u0938\u093e\u0920\u0940 \u092a\u093e\u0924\u094d\u0930 \u0928\u093e\u0939\u0940."
            return "\u274C You are not eligible for any schemes based on current criteria."

        res_parts = []
        for sch in eligible:
            sch_name = sch.get("scheme_name_local") or sch.get("scheme_name")
            benefit = sch.get("annual_benefit")
            docs = ", ".join(sch.get("documents_required", []))
            steps = "\n  ".join([f"{i+1}. {step}" for i, step in enumerate(sch.get("enrollment_steps", []))])
            
            if lang == "hi":
                p = f"\U0001F4CB **{sch_name}**:\n- **\u0932\u093e\u092d**: {benefit}\n- **\u0926\u0938\u094d\u0924\u093e\u0935\u0947\u091c**: {docs}\n- **\u0906\u0935\u0947\u0926\u0928 (Registration) \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e**:\n  {steps}"
            elif lang == "kn":
                p = f"\U0001F4CB **{sch_name}**:\n- **\u0CAA\u0CCD\u0CB0\u0CAF\u0CCB\u0C9C\u0CA8**: {benefit}\n- **\u0CA6\u0CBE\u0C96\u0CB2\u0CC6\u0C97\u0CB3\u0CC1**: {docs}\n- **\u0CA8\u0CCB\u0C82\u0CA6\u0CA3\u0CBF (Registration) \u0CB5\u0CBF\u0CA7\u0CBE\u0CA8**:\n  {steps}"
            elif lang == "te":
                p = f"\U0001F4CB **{sch_name}**:\n- **\u0C2A\u0C4D\u0C30\u0C2F\u0C4B\u0C1C\u0C28\u0C02**: {benefit}\n- **\u0C2A\u0C24\u0C4D\u0C30\u0C3E\u0C32\u0C41**: {docs}\n- **\u0C30\u0C3F\u0C1C\u0C3F\u0C38\u0C4D\u0C1F\u0C4D\u0C30\u0C47\u0C37\u0C28\u0C4D (Registration) \u0C35\u0C3F\u0C27\u0C3E\u0C28\u0C02**:\n  {steps}"
            elif lang == "mr":
                p = f"\U0001F4CB **{sch_name}**:\n- **\u0932\u093e\u092d**: {benefit}\n- **\u0915\u093e\u0917\u0926\u092a\u0924\u094d\u0930\u0947**: {docs}\n- **\u0905\u0930\u094d\u091c (Registration) \u092a\u094d\u0930\u0915\u094d\u0930\u093f\u092f\u093e**:\n  {steps}"
            else:
                p = f"\U0001F4CB **{sch_name}**:\n- **Benefit**: {benefit}\n- **Documents**: {docs}\n- **Registration & Enrollment Steps**:\n  {steps}"
            res_parts.append(p)

        if lang == "hi": return "\U0001F381 **\u092a\u093e\u0924\u094d\u0930 \u0938\u0930\u0915\u093e\u0930\u0940 \u092f\u094b\u091c\u0928\u093e\u090f\u0902**:\n\n" + "\n\n".join(res_parts)
        elif lang == "kn": return "\U0001F381 **\u0C85\u0CB0\u0CCD\u0CB9 \u0CB8\u0CB0\u0CCD\u0C95\u0CBE\u0CB0\u0CBF \u0CAF\u0CCB\u0C9C\u0CA8\u0CC6\u0C97\u0CB3\u0CC1**:\n\n" + "\n\n".join(res_parts)
        elif lang == "te": return "\U0001F381 **\u0C05\u0C30\u0C4D\u0C39\u0C24 \u0C09\u0C28\u0C4D\u0C28 \u0C2A\u0C25\u0C15\u0C3E\u0C32\u0C41**:\n\n" + "\n\n".join(res_parts)
        elif lang == "mr": return "\U0001F381 **\u092a\u093e\u0924\u094d\u0930 \u0938\u0930\u0915\u093e\u0930\u0940 \u092f\u094b\u091c\u0928\u093e**:\n\n" + "\n\n".join(res_parts)
        return "\U0001F381 **Eligible Schemes**:\n\n" + "\n\n".join(res_parts)

    def _format_weather_response(self, data: dict, lang: str) -> str:
        """Helper to format weather advisory localized."""
        adv = data.get("overall_advisory", "")
        alerts = ", ".join(data.get("risk_alerts", []))
        
        if lang == "hi":
            res = f"\u2600\uFE0F **\u092e\u094c\u0938\u092e \u0906\u0927\u093e\u0930\u093f\u0924 \u0915\u0943\u0937\u093f \u0938\u0932\u093e\u0939**:\n- **\u0938\u0932\u093e\u0939**: {adv}\n"
            if alerts: res += f"- **\u091a\u0947\u0924\u093e\u0935\u0928\u0940**: \u26A0\uFE0F {alerts}\n"
            return res
        elif lang == "kn":
            res = f"\u2600\uFE0F **\u0CB9\u0CB5\u0CBE\u0CAE\u0CBE\u0CA8 \u0C86\u0CA7\u0CBE\u0CB0\u0CBF\u0CA4 \u0C95\u0CC3\u0CB7\u0CBF \u0CB8\u0CB2\u0CB9\u0CC6**:\n- **\u0CB8\u0CB2\u0CB9\u0CC6**: {adv}\n"
            if alerts: res += f"- **\u0C8E\u0C9A\u0CCD\u0C9A\u0CB0\u0CBF\u0C95\u0CC6**: \u26A0\uFE0F {alerts}\n"
            return res
        elif lang == "te":
            res = f"\u2600\uFE0F **\u0C35\u0C3E\u0C24\u0C3E\u0C35\u0C30\u0C23 \u0C06\u0C27\u0C3E\u0C30\u0C3F\u0C24 \u0C2A\u0C02\u0C1F \u0C38\u0C32\u0C39\u0C3E**:\n- **\u0C38\u0C32\u0C39\u0C3E**: {adv}\n"
            if alerts: res += f"- **\u0C39\u0C46\u0C1A\u0C4D\u0C1A\u0C30\u0C3F\u0C15**: \u26A0\uFE0F {alerts}\n"
            return res
        elif lang == "mr":
            res = f"\u2600\uFE0F **\u0939\u0935\u093e\u092e\u093e\u0928 \u0906\u0927\u093e\u0930\u093f\u0924 \u0915\u0943\u0937\u0940 \u0938\u0932\u094d\u0932\u093e**:\n- **\u0938\u0932\u094d\u0932\u093e**: {adv}\n"
            if alerts: res += f"- **\u0907\u0936\u093e\u0930\u093e**: \u26A0\uFE0F {alerts}\n"
            return res
        else:
            res = f"\u2600\uFE0F **Weather Advisory**:\n- **Advisory**: {adv}\n"
            if alerts: res += f"- **Alerts**: \u26A0\uFE0F {alerts}\n"
            return res

    def _format_market_response(self, data: dict, lang: str) -> str:
        """Helper to format market price localized."""
        comm = data.get("commodity", "")
        modal = data.get("modal_price_per_quintal", 0)
        msp = data.get("msp_per_quintal", 0)
        diff = data.get("price_vs_msp", "")
        rec = data.get("recommendation", "")
        mandi = data.get("nearest_mandis", [{}])[0].get("mandi_name", "APMC")

        if lang == "hi":
            return f"\U0001F4B0 **\u092e\u0902\u0921\u0940 \u092c\u093e\u091c\u093e\u0930 \u092d\u093e\u0935 ({comm.capitalize()})**:\n- **\u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0926\u0930 ({mandi})**: \u20B9{modal}/\u0915\u094d\u0935\u093f\u0902\u091f\u0932\n- **\u0928\u094d\u092f\u0942\u0928\u0924\u092e \u0938\u092e\u0930\u094d\u0925\u0928 \u092e\u0942\u0932\u094d\u092f (MSP)**: \u20B9{msp}/\u0915\u094d\u0935\u093f\u0902\u091f\u0932 ({diff})\n- **\u0938\u0941\u091d\u093e\u0935**: {rec}"
        elif lang == "kn":
            return f"\U0001F4B0 **\u0CAE\u0CBE\u0CB0\u0CC1\u0C95\u0C9F\u0CCD\u0C9F\u0CC6 \u0CA7\u0CBE\u0CB0\u0CA3\u0CC6 ({comm.capitalize()})**:\n- **\u0CAA\u0CCD\u0CB0\u0CB8\u0CCD\u0CA4\u0CC1\u0CA4 \u0CA6\u0CB0 ({mandi})**: \u20B9{modal}/\u0C95\u0CCD\u0CB5\u0CBF\u0C82\u0C9F\u0CB2\u0CCD\n- **\u0C95\u0CA8\u0CBF\u0CB7\u0CCD\u0CA0 \u0CAC\u0CC6\u0C82\u0CAC\u0CB2 \u0CAC\u0CC6\u0CB2\u0CC6 (MSP)**: \u20B9{msp}/\u0C95\u0CCD\u0CB5\u0CBF\u0C82\u0C9F\u0CB2\u0CCD ({diff})\n- **\u0CB6\u0CBF\u0CAB\u0CBE\u0CB0\u0CB8\u0CC1**: {rec}"
        elif lang == "te":
            return f"\U0001F4B0 **\u0C2E\u0C3E\u0C30\u0C4D\u0C15\u0C46\u0C1F\u0C4D \u0C27\u0C30 ({comm.capitalize()})**:\n- **\u0C2A\u0C4D\u0C30\u0C38\u0C4D\u0C24\u0C41\u0C24 \u0C27\u0C30 ({mandi})**: \u20B9{modal}/\u0C15\u0C4D\u0C35\u0C3F\u0C02\u0C1F\u0C3E\u0C32\u0C4D\n- **\u0C15\u0C28\u0C40\u0C38 \u0C2E\u0C26\u0C4D\u0C26\u0C24\u0C41 \u0C27\u0C30 (MSP)**: \u20B9{msp}/\u0C15\u0C4D\u0C35\u0C3F\u0C02\u0C1F\u0C3E\u0C32\u0C4D ({diff})\n- **\u0C38\u0C32\u0C39\u0C3E**: {rec}"
        elif lang == "mr":
            return f"\U0001F4B0 **\u092e\u0902\u0921\u0940 \u092c\u093e\u091c\u093e\u0930\u092d\u093e\u0935 ({comm.capitalize()})**:\n- **\u0938\u0927\u094d\u092f\u093e\u091a\u093e \u0926\u0930 ({mandi})**: \u20B9{modal}/\u0915\u094d\u0935\u093f\u0902\u091f\u0932\n- **\u0915\u093f\u092e\u093e\u0928 \u0906\u0927\u093e\u0930\u092d\u0942\u0924 \u0915\u093f\u0902\u092e\u0924 (MSP)**: \u20B9{msp}/\u0915\u094d\u0935\u093f\u0902\u091f\u0932 ({diff})\n- **\u0938\u0932\u094d\u0932\u093e**: {rec}"
        else:
            return f"\U0001F4B0 **Market Price ({comm.capitalize()})**:\n- **Current Price ({mandi})**: \u20B9{modal}/quintal\n- **MSP**: \u20B9{msp}/quintal ({diff})\n- **Recommendation**: {rec}"
