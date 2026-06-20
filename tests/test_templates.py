from app.domain.enums import Language
from app.services.templates import get_body, render_template


class _FakeLead:
    def __init__(self, name: str, model: str | None, language: Language) -> None:
        self.name = name
        self.interested_model = model
        self.preferred_language = language


def test_render_substitutes_placeholders() -> None:
    text = render_template("day0_thankyou", _FakeLead("Ravi", "Nexon", Language.EN))
    assert "Ravi" in text
    assert "Nexon" in text


def test_render_handles_missing_model() -> None:
    text = render_template("day2_modelinfo", _FakeLead("Asha", None, Language.EN))
    assert "Asha" in text
    assert "{model}" not in text


def test_language_variants_present() -> None:
    assert get_body("day0_thankyou", Language.TE)
    assert get_body("day0_thankyou", Language.HI)
    # Unknown step would KeyError; known step always has English.
    assert get_body("day9_final", Language.EN)
