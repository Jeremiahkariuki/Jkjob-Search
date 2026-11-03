"""
Strict EMEA & Kenya Eligibility Verification Engine.
Enforces the mandatory location criteria defined in Section 3:
- Confirmed eligible: Explicitly accepts Kenya, Africa, EMEA, or Worldwide/Anywhere.
- Potentially eligible: Remote/International, but exact location boundaries unconfirmed.
- Not eligible: Excludes Kenya/EMEA or requires residence in incompatible regions (US, EU, UK only).
"""
import re
from typing import Tuple

class EligibilityEngine:
    CONFIRMED = "Confirmed eligible"
    POTENTIAL = "Potentially eligible"
    NOT_ELIGIBLE = "Not eligible"

    # Incompatible location patterns
    EXCLUSION_PATTERNS = [
        r"\b(us\s*only|usa\s*only|united\s*states\s*only)\b",
        r"\b(north\s*america\s*only|canada\s*only)\b",
        r"\b(uk\s*only|united\s*kingdom\s*only|must\s*reside\s*in\s*the\s*uk)\b",
        r"\b(eu\s*only|european\s*union\s*only|must\s*be\s*located\s*in\s*the\s*eu)\b",
        r"\b(germany\s*only|france\s*only|netherlands\s*only|poland\s*only)\b",
        r"\b(latam\s*only|latin\s*america\s*only|apac\s*only|australia\s*only)\b",
        r"\b(us\s*citizenship\s*required|must\s*have\s*us\s*work\s*authorization)\b",
        r"\b(no\s*sponsorship\s*available\s*for\s*us)\b",
        r"\b(must\s*reside\s*in\s*the\s*united\s*states)\b",
        r"\b(remote\s*-\s*us\b|remote\s*\(us\)|remote\s*usa)\b",
        r"\b(remote\s*-\s*canada|remote\s*-\s*uk|remote\s*-\s*germany)\b",
    ]

    # Explicit Kenya / EMEA / Worldwide patterns
    CONFIRMED_PATTERNS = [
        r"\b(kenya|nairobi|mombasa|kisumu)\b",
        r"\b(africa|sub-saharan\s*africa|east\s*africa)\b",
        r"\b(emea|europe\s*middle\s*east\s*and\s*africa)\b",
        r"\b(worldwide|anywhere|global\s*remote|remote\s*worldwide|anywhere\s*in\s*the\s*world)\b",
        r"\b(work\s*from\s*anywhere|location\s*independent|100%\s*global)\b",
        r"\b(utc\s*[\+\-]\s*[1-4]|eat\s*timezone|gmt\s*[\+\-]\s*[1-4])\b"
    ]

    @classmethod
    def evaluate(cls, location_text: str, description_text: str = "") -> Tuple[str, str]:
        """
        Evaluates location eligibility.
        Returns: (status, supporting_evidence)
        """
        combined = f"{location_text} {description_text}".lower()
        loc_lower = location_text.lower().strip()

        # Check explicit exclusions first
        for pat in cls.EXCLUSION_PATTERNS:
            if re.search(pat, loc_lower) or re.search(pat, combined[:500]):
                match = re.search(pat, loc_lower) or re.search(pat, combined[:500])
                return cls.NOT_ELIGIBLE, f"Explicit regional restriction detected: '{match.group(0)}'"

        # Check explicit confirmed matches
        for pat in cls.CONFIRMED_PATTERNS:
            m_loc = re.search(pat, loc_lower)
            if m_loc:
                return cls.CONFIRMED, f"Listing location explicitly allows target region: '{m_loc.group(0)}'"

        # Check description for confirmed terms
        for pat in cls.CONFIRMED_PATTERNS:
            m_desc = re.search(pat, combined)
            if m_desc:
                return cls.CONFIRMED, f"Listing description explicitly confirms EMEA/Africa/Global hiring: '{m_desc.group(0)}'"

        # Ambiguous remote
        if "remote" in loc_lower or "remote" in combined[:300] or "anywhere" in combined:
            return cls.POTENTIAL, "Marked as Remote/International, but specific allowed countries/entities are not explicitly declared."

        return cls.NOT_ELIGIBLE, f"Location '{location_text}' does not explicitly confirm EMEA/Kenya or global eligibility."
