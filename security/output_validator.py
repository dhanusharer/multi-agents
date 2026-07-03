import re
from typing import Optional, Tuple, List

class OutputValidator:
    """Post-processing validator for all agent responses."""

    ALLOWED_DOMAINS = [
        "pmkisan.gov.in", "agmarknet.gov.in", "icar.org.in",
        "data.gov.in", "pmfby.gov.in", "pmkusum.mnre.gov.in",
        "enam.gov.in", "soilhealth.dac.gov.in",
        "agrimachinery.nic.in", "kvk.icar.org.in"
    ]

    BLOCKED_PHRASES = [
        "as an ai", "i'm just a language model", "i cannot help",
        "i don't have access", "hallucin", "i'm not sure but",
        "i think maybe", "api_key=", "secret=", "password=",
        "token=", "```python", "```javascript", "```sql",
    ]

    MAX_RESPONSE_LENGTH = 15000  # characters

    def validate(self, response: str, farmer_name: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate agent response before returning it to the user.
        
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []

        if not response or not response.strip():
            violations.append("Empty response")
            return False, violations

        # Check 1: PII leak
        if farmer_name and farmer_name.lower() in response.lower():
            violations.append(f"PII leak: farmer name '{farmer_name}' detected")

        # Check 2: Code blocks
        if "```" in response or "<code>" in response or "</code" in response:
            violations.append("Code block detected")

        # Check 3: Off-domain URLs
        urls = re.findall(r"https?://[^\s/$.?#].[^\s]*", response)
        for url in urls:
            domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
            if domain_match:
                domain = domain_match.group(1).lower()
                if not any(allowed in domain for allowed in self.ALLOWED_DOMAINS):
                    violations.append(f"Off-domain URL detected: {url}")

        # Check 4: Blocked phrases & secrets
        lower_resp = response.lower()
        for phrase in self.BLOCKED_PHRASES:
            if phrase in lower_resp:
                violations.append(f"Blocked phrase/code marker: '{phrase}'")

        # Check 5: Response length
        if len(response) > self.MAX_RESPONSE_LENGTH:
            violations.append(f"Response length exceeds {self.MAX_RESPONSE_LENGTH} chars (got {len(response)})")

        return len(violations) == 0, violations

    def sanitize_response(self, response: str) -> str:
        """Clean minor issues from output response (like extra whitespace or trailing code tags)."""
        cleaned = response.strip()
        # Remove any lingering code markdown block tags
        cleaned = cleaned.replace("```python", "").replace("```html", "").replace("```", "")
        return cleaned

    def get_safe_error_message(self, language: str) -> str:
        """Return culturally appropriate safe response fallback in the farmer's language."""
        messages = {
            "hi": "क्षमा करें, मैं इस समय सुरक्षित उत्तर उत्पन्न करने में असमर्थ हूँ। कृपया अपने प्रश्न को फिर से लिखें या स्थानीय कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",
            "kn": "ಕ್ಷಮಿಸಿ, ಸುರಕ್ಷಿತ ಪ್ರತಿಕ್ರಿಯೆಯನ್ನು ನೀಡಲು ಸಾಧ್ಯವಾಗುತ್ತಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಮತ್ತೊಮ್ಮೆ ಕೇಳಿ ಅಥವಾ ಸ್ಥಳೀಯ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
            "te": "క్షమించండి, ప్రస్తుతం సురక్షితమైన సమాధానం ఇవ్వలేకపోతున్నాను. దయచేసి మీ ప్రశ్నను మార్చి అడగండి లేదా స్థానిక కృషి విజ్ఞాన కేంద్రాన్ని సంప్రదించండి.",
            "mr": "क्षमस्व, मी या वेळी सुरक्षित उत्तर देण्यास असमर्थ आहे. कृपया आपला प्रश्न पुन्हा विचारा किंवा जवळच्या कृषी विज्ञान केंद्राशी संपर्क साधा.",
            "en": "I apologize, but I am unable to generate a safe response at this time. Please rephrase your query or contact your local Krishi Vigyan Kendra (KVK)."
        }
        return messages.get(language.lower(), messages["en"])
