"""Deterministic pre-send guardrail.

The prompt tells the model never to quote prices etc., but this is the backstop:
if a draft reply contains a forbidden specific (a currency figure, a lakh/crore
amount, a percentage, an EMI number), we block it before it reaches the customer
and escalate to a human instead.
"""
from __future__ import annotations

import re

_FORBIDDEN = [
    re.compile(r"₹\s*\d"),
    re.compile(r"\brs\.?\s*\d", re.IGNORECASE),
    re.compile(r"\binr\s*\d", re.IGNORECASE),
    re.compile(r"\d[\d,]*\s*(lakh|lakhs|crore|cr)\b", re.IGNORECASE),
    re.compile(r"\d+\s*%"),
    re.compile(r"\bemi\b[^.\n]*\d", re.IGNORECASE),
]

SAFE_FALLBACK = {
    "en": (
        "Thanks for your question! For the exact details, let me connect you with our sales "
        "team - they'll reach out shortly. Anything else I can help with? 🙂"
    ),
    "hi": (
        "आपके सवाल के लिए धन्यवाद! इसकी सटीक जानकारी के लिए मैं आपको हमारी सेल्स टीम से जोड़ देता हूँ "
        "- वे जल्द ही आपसे संपर्क करेंगे। और किसी चीज़ में मदद करूँ? 🙂"
    ),
    "te": (
        "మీ ప్రశ్నకు ధన్యవాదాలు! ఖచ్చితమైన వివరాల కోసం మిమ్మల్ని మా సేల్స్ టీమ్‌తో కలుపుతాను "
        "- వారు త్వరలో మిమ్మల్ని సంప్రదిస్తారు. ఇంకేమైనా సహాయం కావాలా? 🙂"
    ),
}


def guardrail_check(text: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means the text must not be sent as-is."""
    for pattern in _FORBIDDEN:
        match = pattern.search(text)
        if match:
            return False, f"forbidden content {match.group(0)!r}"
    return True, ""


def safe_fallback(language: str) -> str:
    return SAFE_FALLBACK.get(language, SAFE_FALLBACK["en"])
