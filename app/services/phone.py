"""Phone normalization to E.164 for Indian numbers (the dedupe key).

Pragmatic and dependency-free; covers the formats staff actually type. If the
product ever goes multi-country, swap this for the `phonenumbers` library.
"""
from __future__ import annotations

import re

_NON_DIGITS = re.compile(r"\D")


class PhoneError(ValueError):
    """Raised when a value cannot be normalized to a valid Indian mobile."""


def normalize_phone(raw: str, default_cc: str = "91") -> str:
    """Return ``+91XXXXXXXXXX`` or raise :class:`PhoneError`.

    Accepts e.g. ``98765 43210``, ``098765-43210``, ``+91 98765 43210``,
    ``0091 9876543210``.
    """
    if not raw or not raw.strip():
        raise PhoneError("empty phone number")

    digits = _NON_DIGITS.sub("", raw)

    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == len(default_cc) + 10 and digits.startswith(default_cc):
        digits = digits[len(default_cc):]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10:
        raise PhoneError(f"not a 10-digit Indian number: {raw!r}")
    if digits[0] not in "6789":
        raise PhoneError(f"invalid Indian mobile prefix: {raw!r}")

    return f"+{default_cc}{digits}"
