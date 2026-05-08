from __future__ import annotations

import re
from dataclasses import dataclass

ENTITY_PREFIX = r"(?:ООО|АО|ПАО|ЗАО|ИП|ОАО|НКО|АНО|ФГУП|ГУП)"
NAME_QUOTED = r'"[^"]+"'
NAME_UNQUOTED = r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.[А-ЯЁ]\.)?"
NAME_PATTERN = rf"(?:{NAME_QUOTED}|{NAME_UNQUOTED})"
ENTITY = rf"{ENTITY_PREFIX}\s+{NAME_PATTERN}"
ROLE_QUOTED = r'"([^"]+)"'
ENTITY_START = re.compile(
    rf"(?=(?<![А-ЯЁа-яё]){ENTITY_PREFIX}\s+(?:\"|[А-ЯЁ]))", re.IGNORECASE
)

PATTERN_DALEE_QUOTED = re.compile(
    rf"({ENTITY}).*?(?:именуем(?:ое|ый|ая)\s+в\s+дальнейшем)\s+{ROLE_QUOTED}",
    re.IGNORECASE,
)
PATTERN_DALEE_DASH = re.compile(
    rf"({ENTITY}).*?\(\s*далее\s*[—-]\s*([А-ЯЁ][а-яё]+)\s*\)",
    re.IGNORECASE,
)


@dataclass
class ExtractedParty:
    name: str
    role: str
    confidence: float


def _entity_spans(preamble_text: str) -> list[str]:
    starts = [m.start() for m in ENTITY_START.finditer(preamble_text)]
    return [
        preamble_text[start : starts[index + 1] if index + 1 < len(starts) else len(preamble_text)]
        for index, start in enumerate(starts)
    ]


class PartyExtractor:
    def extract(self, preamble_text: str) -> list[ExtractedParty]:
        seen: dict[str, ExtractedParty] = {}
        for span in _entity_spans(preamble_text):
            m = PATTERN_DALEE_QUOTED.search(span)
            if m:
                name = m.group(1).strip()
                role = m.group(2).strip()
                seen[role] = ExtractedParty(name=name, role=role, confidence=0.9)

            m = PATTERN_DALEE_DASH.search(span)
            if m:
                name = m.group(1).strip()
                role = m.group(2).strip()
                seen.setdefault(role, ExtractedParty(name=name, role=role, confidence=0.85))
        return list(seen.values())
