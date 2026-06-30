"""Normalize extracted date values to a consistent, language-specific format.

Date-typed columns (per the template's ``data_type``) can come back from the LLM
in many shapes — ``17/09/2026``, ``2026-09-17``, ``17 de septiembre de 2026``,
``September 17, 2026`` — sometimes with a trailing time. We normalize them to a
single per-language form (todo #8 / ADR-0012):

- Spanish session: ``DD-mmm-YYYY`` with a Spanish month abbreviation, e.g.
  ``17-sep-2026``.
- English session: ``MM/DD/YYYY`` (US order), e.g. ``09/17/2026``.

The session language also disambiguates numeric input: ``03/04/2026`` is read as
DD/MM in Spanish and MM/DD in English. Values we cannot confidently parse as a
date are returned unchanged, so content we do not understand is never corrupted.
"""

import re
from datetime import datetime

# Spanish 3-letter month abbreviations, indexed 1..12 — the Spanish output form.
_MONTH_ABBR_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

# Month names/abbreviations (Spanish + English) → month number, for textual dates.
_MONTH_NAMES = {
    # Spanish
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "set": 9, "sept": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
    # English
    "january": 1, "jan": 1,
    "february": 2,
    "march": 3,
    "april": 4, "apr": 4,
    "june": 6,
    "july": 7,
    "august": 8, "aug": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12, "dec": 12,
}

# Numeric date layouts by language, tried in order. The day/month order differs
# (DD/MM for Spanish, MM/DD for English); ISO is unambiguous and shared.
_NUMERIC_FORMATS = {
    "es": ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"),
    "en": ("%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m-%d-%y"),
}

# Textual dates. DMY: "17 de septiembre de 2026", "17 September 2026".
_TEXTUAL_DMY = re.compile(
    r"(\d{1,2})\s*(?:de\s+|del\s+|of\s+)?([a-záéíóúñ]+)\.?,?\s*(?:de\s+|del\s+)?(\d{4})",
    re.IGNORECASE,
)
# MDY: "September 17, 2026", "Sep 17 2026".
_TEXTUAL_MDY = re.compile(
    r"([a-záéíóúñ]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
    re.IGNORECASE,
)


def is_date_type(data_type: str) -> bool:
    """Return True if a column's ``data_type`` denotes a date.

    Matches the Spanish "fecha" (e.g. ``fecha DD/MM/YYYY``) and the English
    "date", regardless of the surrounding format hint.
    """
    dt = data_type.strip().lower()
    return "fecha" in dt or "date" in dt


def normalize_date_value(value: str, language: str = "es") -> str:
    """Reformat ``value`` as a date in the session ``language``.

    Spanish → ``DD-mmm-YYYY`` (Spanish month abbreviation); English →
    ``MM/DD/YYYY``. Any time component is dropped. The original value is returned
    unchanged when it is empty or cannot be parsed as a date.
    """
    raw = value.strip()
    if not raw:
        return value

    lang = language if language in _NUMERIC_FORMATS else "es"
    parsed = _try_numeric(raw, lang) or _try_textual(raw)
    if parsed is None:
        return value

    day, month, year = parsed
    if lang == "en":
        return f"{month:02d}/{day:02d}/{year}"
    return f"{day:02d}-{_MONTH_ABBR_ES[month]}-{year}"


def _try_numeric(raw: str, language: str) -> tuple[int, int, int] | None:
    """Parse purely numeric dates (language sets the day/month order), dropping time."""
    token = raw.split()[0].split("T")[0]
    for fmt in _NUMERIC_FORMATS[language]:
        try:
            d = datetime.strptime(token, fmt)
        except ValueError:
            continue
        return d.day, d.month, d.year
    return None


def _try_textual(raw: str) -> tuple[int, int, int] | None:
    """Parse dates with a Spanish or English month name, in DMY or MDY order."""
    dmy = _TEXTUAL_DMY.search(raw)
    if dmy:
        result = _resolve_textual(dmy.group(1), dmy.group(2), dmy.group(3))
        if result is not None:
            return result

    mdy = _TEXTUAL_MDY.search(raw)
    if mdy:
        return _resolve_textual(mdy.group(2), mdy.group(1), mdy.group(3))

    return None


def _resolve_textual(day_str: str, month_str: str, year_str: str) -> tuple[int, int, int] | None:
    """Validate a (day, month-name, year) triple and return numeric parts."""
    month = _MONTH_NAMES.get(month_str.lower())
    if month is None:
        return None
    day = int(day_str)
    year = int(year_str)
    try:
        datetime(year, month, day)  # validate the calendar date
    except ValueError:
        return None
    return day, month, year
