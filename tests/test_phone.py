import pytest

from app.services.phone import PhoneError, normalize_phone


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("098765-43210", "+919876543210"),
        ("0091 9876543210", "+919876543210"),
        ("+919876543210", "+919876543210"),
        ("(98765) 43210", "+919876543210"),
    ],
)
def test_normalize_valid(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "12345", "1234567890", "98765"])
def test_normalize_invalid(raw: str) -> None:
    with pytest.raises(PhoneError):
        normalize_phone(raw)
