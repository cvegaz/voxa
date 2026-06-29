"""Normalize extracted date values to a consistent ``DD-mmm-YYYY`` display format.

Date-typed columns (per the template's ``data_type``) can come back from the LLM
in many shapes — ``17/09/2026``, ``2026-09-17``, ``17 de septiembre de 2026``,
sometimes with a trailing time. We normalize them to a single human-friendly form
like ``17-sep-2026`` (Spanish month abbreviation, no time component).

Values we cannot confidently parse as a date are returned unchanged, so content we
do not understand is never lost or corrupted.
"""

import re
from datetime import datetime

# Spanish 3-letter month abbreviations, indexed 1..12 — the output form.
_MONTH_ABBR = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

# Spanish month names and abbreviations → month number, for textual dates.
_MONTH_NAMES = {
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
}

# Numeric date layouts, tried in order. 4-digit-year variants come first so a
# value like "17/09/2026" is never mis-read by a 2-digit-year pattern.
_NUMERIC_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%y", "%d-%m-%y",
)

# Textual dates such as "17 de septiembre de 2026" or "17 sep 2026".
_TEXTUAL_RE = re.compile(
    r"(\d{1,2})\s*(?:de\s+|del\s+)?([a-záéíóúñ]+)\.?\s*(?:de\s+|del\s+)?(\d{4})",
    re.IGNORECASE,
)


def is_date_type(data_type: str) -> bool:
    """Return True if a column's ``data_type`` denotes a date.

    Matches the Spanish "fecha" (e.g. ``fecha DD/MM/YYYY``) and the English
    "date", regardless of the surrounding format hint.
    """
    dt = data_type.strip().lower()
    return "fecha" in dt or "date" in dt


def normalize_date_value(value: str) -> str:
    """Reformat ``value`` as ``DD-mmm-YYYY`` (e.g. ``17-sep-2026``).

    The day is zero-padded and the month is a lowercase Spanish abbreviation; any
    time component is dropped. The original value is returned unchanged when it is
    empty or cannot be parsed as a date.
    """
    raw = value.strip()
    if not raw:
        return value

    parsed = _try_numeric(raw) or _try_textual(raw)
    if parsed is None:
        return value

    day, month, year = parsed
    return f"{day:02d}-{_MONTH_ABBR[month]}-{year}"


def _try_numeric(raw: str) -> tuple[int, int, int] | None:
    """Parse purely numeric dates, dropping any trailing time."""
    token = raw.split()[0].split("T")[0]
    for fmt in _NUMERIC_FORMATS:
        try:
            d = datetime.strptime(token, fmt)
        except ValueError:
            continue
        return d.day, d.month, d.year
    return None


def _try_textual(raw: str) -> tuple[int, int, int] | None:
    """Parse dates with a Spanish month name/abbreviation."""
    match = _TEXTUAL_RE.search(raw)
    if not match:
        return None

    day = int(match.group(1))
    month = _MONTH_NAMES.get(match.group(2).lower())
    year = int(match.group(3))
    if month is None:
        return None

    try:
        datetime(year, month, day)  # validate the calendar date
    except ValueError:
        return None
    return day, month, year
