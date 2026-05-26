from __future__ import annotations

import re
from dataclasses import dataclass

MONTHS = {
    "JAN": "JAN",
    "JANUARY": "JAN",
    "FEB": "FEB",
    "FEBRUARY": "FEB",
    "MAR": "MAR",
    "MARCH": "MAR",
    "APR": "APR",
    "APRIL": "APR",
    "MAY": "MAY",
    "JUN": "JUN",
    "JUNE": "JUN",
    "JUL": "JUL",
    "JULY": "JUL",
    "AUG": "AUG",
    "AUGUST": "AUG",
    "SEP": "SEP",
    "SEPT": "SEP",
    "SEPTEMBER": "SEP",
    "OCT": "OCT",
    "OCTOBER": "OCT",
    "NOV": "NOV",
    "NOVEMBER": "NOV",
    "DEC": "DEC",
    "DECEMBER": "DEC",
}

QUALIFIERS = {
    "ABOUT": "ABT",
    "ABT": "ABT",
    "ABT.": "ABT",
    "AFTER": "AFT",
    "AFT": "AFT",
    "AFT.": "AFT",
    "BEFORE": "BEF",
    "BEF": "BEF",
    "BEF.": "BEF",
    "CAL": "CAL",
    "CAL.": "CAL",
    "EST": "EST",
    "EST.": "EST",
}

COUNTRY_ALIASES = {
    "USA": "USA",
    "UNITED STATES": "USA",
    "UNITED STATES OF AMERICA": "USA",
    "U.S.": "USA",
    "U.S.A.": "USA",
    "US": "USA",
}

STATE_ALIASES = {
    "KY": "Kentucky",
    "KENTUCKY": "Kentucky",
    "VA": "Virginia",
    "VIRGINIA": "Virginia",
    "IN": "Indiana",
    "INDIANA": "Indiana",
    "IL": "Illinois",
    "ILLINOIS": "Illinois",
    "MA": "Massachusetts",
    "MASSACHUSETTS": "Massachusetts",
    "MO": "Missouri",
    "MISSOURI": "Missouri",
    "NC": "North Carolina",
    "NORTH CAROLINA": "North Carolina",
    "OH": "Ohio",
    "OHIO": "Ohio",
    "WI": "Wisconsin",
    "WISCONSIN": "Wisconsin",
}


@dataclass(frozen=True)
class DateNormalization:
    raw: str
    normalized: str | None
    year: int | None
    changed: bool
    parseable: bool
    gedcom_standard: bool


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def title_case_name(value: str) -> str:
    parts = []
    for part in normalize_spaces(value).split(" "):
        if part.startswith('"') and len(part) > 1:
            parts.append('"' + part[1:].capitalize())
        elif part.endswith('"') and len(part) > 1:
            parts.append(part[:-1].capitalize() + '"')
        elif part.upper() in {"II", "III", "IV", "VI"}:
            parts.append(part.upper())
        else:
            parts.append(part.capitalize())
    return " ".join(parts)


def normalize_gedcom_date(raw: str | None) -> DateNormalization | None:
    if not raw:
        return None

    original = raw
    value = normalize_spaces(raw).replace("/", " ")
    upper = value.upper()
    qualifier = None

    tokens = upper.split()
    if tokens and tokens[0] in QUALIFIERS:
        qualifier = QUALIFIERS[tokens[0]]
        tokens = tokens[1:]

    normalized = _normalize_date_tokens(tokens)
    if normalized and qualifier:
        normalized = f"{qualifier} {normalized}"

    year = _extract_year(normalized or value)
    gedcom_standard = bool(normalized and _GEDCOM_DATE_RE.match(normalized))
    return DateNormalization(
        raw=original,
        normalized=normalized,
        year=year,
        changed=bool(normalized and normalized != original),
        parseable=normalized is not None,
        gedcom_standard=gedcom_standard and normalized == original,
    )


def normalize_place(raw: str | None) -> str | None:
    if not raw:
        return None

    parts = [normalize_spaces(p).strip(" .") for p in raw.split(",")]
    parts = [p for p in parts if p]
    normalized_parts = []

    for index, part in enumerate(parts):
        key = part.upper()
        if index == len(parts) - 1 and key in COUNTRY_ALIASES:
            candidate = COUNTRY_ALIASES[key]
        elif key in STATE_ALIASES:
            candidate = STATE_ALIASES[key]
        elif part.isupper():
            candidate = title_case_name(part)
        else:
            candidate = part

        if not normalized_parts or normalized_parts[-1].lower() != candidate.lower():
            normalized_parts.append(candidate)

    return ", ".join(normalized_parts)


def normalize_person_name(raw: str | None) -> str | None:
    if not raw:
        return None
    value = normalize_spaces(raw.replace("/", ""))
    if not value:
        return None
    return title_case_name(value) if value.isupper() else value


def normalized_identity_key(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _normalize_date_tokens(tokens: list[str]) -> str | None:
    if not tokens:
        return None

    if len(tokens) == 1 and re.fullmatch(r"\d{4}", tokens[0]):
        return tokens[0]

    if len(tokens) == 2 and tokens[0] in MONTHS and re.fullmatch(r"\d{4}", tokens[1]):
        return f"{MONTHS[tokens[0]]} {tokens[1]}"

    if len(tokens) == 3 and re.fullmatch(r"\d{1,2}", tokens[0]) and tokens[1] in MONTHS:
        if re.fullmatch(r"\d{4}", tokens[2]):
            return f"{int(tokens[0])} {MONTHS[tokens[1]]} {tokens[2]}"

    return None


def _extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(\d{4})\b", value)
    return int(match.group(1)) if match else None


_GEDCOM_DATE_RE = re.compile(
    r"^(ABT |AFT |BEF |CAL |EST )?((\d{1,2} )?(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) )?\d{4}$"
)
