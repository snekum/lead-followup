from app.assistant.guardrail import guardrail_check, safe_fallback


def test_blocks_forbidden_specifics():
    assert not guardrail_check("It costs around ₹10 lakh on-road")[0]
    assert not guardrail_check("Get 15% off this week")[0]
    assert not guardrail_check("EMI starts around 8000 a month")[0]
    assert not guardrail_check("Rs 50000 as down payment")[0]


def test_allows_safe_replies():
    assert guardrail_check("The Nexon has 5 seats and a 5-star safety rating!")[0]
    assert guardrail_check("Our sales team will share the exact price with you.")[0]
    assert guardrail_check("Would you like to book a test drive? 🚗")[0]


def test_fallback_has_all_languages():
    assert safe_fallback("hi")
    assert safe_fallback("te")
    assert safe_fallback("unknown") == safe_fallback("en")
