from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

ENTITY_PREFIXES = (
    "Федеральное государственное унитарное предприятие",
    "Государственное унитарное предприятие",
    "Общество с ограниченной ответственностью",
    "Публичное акционерное общество",
    "Закрытое акционерное общество",
    "Открытое акционерное общество",
    "Автономная некоммерческая организация",
    "Некоммерческая организация",
    "Акционерное общество",
    "Индивидуальный предприниматель",
    "ООО",
    "АО",
    "ПАО",
    "ЗАО",
    "ИП",
    "ОАО",
    "НКО",
    "АНО",
    "ФГУП",
    "ГУП",
)
ENTITY_PREFIX = rf"(?:{'|'.join(re.escape(prefix) for prefix in ENTITY_PREFIXES)})"
QUOTE_PATTERNS = (
    r'"[^"]+"',
    r"«(?:[^«»]|«[^«»]*»)+»",
    r"„[^“]+“",
    r"“[^”]+”",
    r"”[^”]+”",
    r"”[^“]+“",
)
QUOTED_TEXT = rf"(?:{'|'.join(QUOTE_PATTERNS)})"
NAME_QUOTED = QUOTED_TEXT
NAME_UNQUOTED = r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.[А-ЯЁ]\.)?"
NAME_PATTERN = rf"(?:{NAME_QUOTED}|{NAME_UNQUOTED})"
ENTITY = rf"{ENTITY_PREFIX}\s+{NAME_PATTERN}"
ROLE_QUOTED = QUOTED_TEXT
ENTITY_START = re.compile(
    rf"(?<![А-ЯЁа-яё]){ENTITY}",
    re.IGNORECASE | re.DOTALL,
)

PATTERN_DALEE_QUOTED = re.compile(
    rf"(?P<name>{ENTITY}).*?(?:именуем(?:ое|ый|ая)\s+в\s+дальнейшем)\s+(?P<role>{ROLE_QUOTED})",
    re.IGNORECASE | re.DOTALL,
)
PATTERN_DALEE_DASH = re.compile(
    rf"(?P<name>{ENTITY}).*?\(\s*далее\s*[—-]\s*(?P<role>[А-ЯЁ][а-яё]+)\s*\)",
    re.IGNORECASE | re.DOTALL,
)

_QUOTE_CHARS = '"«»„“”'
_IN_FACE_MARKER = re.compile(r"\bв\s+лице\b", re.IGNORECASE)
_ROLE_MARKER = re.compile(
    r"именуем\w*|\bдалее\b",
    re.IGNORECASE,
)
_PARTY_SEPARATOR = re.compile(
    rf",\s*и\s*(?:юридическое лицо\s+)?(?={ENTITY_PREFIX}\s|$)",
    re.IGNORECASE,
)


@dataclass
class ExtractedParty:
    name: str
    role: str
    confidence: float


def _is_unfinished_in_face_clause(
    preamble_text: str,
    previous_start: int,
    candidate_start: int,
) -> bool:
    segment = preamble_text[previous_start:candidate_start]
    face_matches = list(_IN_FACE_MARKER.finditer(segment))
    if not face_matches:
        return False

    separator_matches = list(_PARTY_SEPARATOR.finditer(segment))
    if separator_matches and separator_matches[-1].start() > face_matches[-1].start():
        return False

    role_matches = list(_ROLE_MARKER.finditer(segment))
    return not role_matches or face_matches[-1].start() > role_matches[-1].start()


def _entity_starts(preamble_text: str, check_budget: Callable[[], None]) -> list[int]:
    starts: list[int] = []
    for match in ENTITY_START.finditer(preamble_text):
        check_budget()
        candidate_start = match.start()
        previous_start = starts[-1] if starts else 0
        if _is_unfinished_in_face_clause(
            preamble_text,
            previous_start,
            candidate_start,
        ):
            continue
        starts.append(candidate_start)
    return starts


def _entity_spans(preamble_text: str, check_budget: Callable[[], None]) -> list[str]:
    starts = _entity_starts(preamble_text, check_budget)
    return [
        preamble_text[start : starts[index + 1] if index + 1 < len(starts) else len(preamble_text)]
        for index, start in enumerate(starts)
    ]


def _strip_quotes(value: str) -> str:
    return value.strip().strip(_QUOTE_CHARS).strip()


class PartyExtractor:
    def extract(self, preamble_text: str, check_budget: Callable[[], None] = lambda: None) -> list[ExtractedParty]:
        check_budget()
        seen: dict[str, ExtractedParty] = {}
        for span in _entity_spans(preamble_text, check_budget):
            check_budget()
            m = PATTERN_DALEE_QUOTED.search(span)
            if m:
                name = m.group("name").strip()
                role = _strip_quotes(m.group("role"))
                seen[role] = ExtractedParty(name=name, role=role, confidence=0.9)

            m = PATTERN_DALEE_DASH.search(span)
            if m:
                name = m.group("name").strip()
                role = m.group("role").strip()
                seen.setdefault(role, ExtractedParty(name=name, role=role, confidence=0.85))
        check_budget()
        return list(seen.values())
