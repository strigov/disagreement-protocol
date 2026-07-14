from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO

from lxml import etree

from app.processing.types import (
    NumberingData, RawDocument, RawParagraph, ResolverDiagnostic,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REGEX_NUMBER = re.compile(r"^\s*(?:Статья\s+)?(\d+(?:\.\d+)*\.?)\s+", re.IGNORECASE)
LOW_CONFIDENCE_THRESHOLD = 0.85
_PLACEHOLDER = re.compile(r"%(\d)")
_MAX_STYLE_CHAIN = 10

_ROMAN = (
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
    (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
)
# Word's russian numbering alphabet: no ё, й, ъ, ы, ь.
_RUSSIAN_LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"

NumberingResolveResult = tuple[dict[str, NumberingData], list[ResolverDiagnostic]]


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _format_value(value: int, num_fmt: str) -> str:
    if value < 1:
        value = 1
    if num_fmt == "decimalZero":
        return str(value).zfill(2)
    if num_fmt in ("lowerLetter", "upperLetter"):
        letter = chr(ord("a") + (value - 1) % 26) * ((value - 1) // 26 + 1)
        return letter.upper() if num_fmt == "upperLetter" else letter
    if num_fmt in ("lowerRoman", "upperRoman"):
        out, rest = [], value
        for weight, sym in _ROMAN:
            while rest >= weight:
                out.append(sym)
                rest -= weight
        roman = "".join(out)
        return roman.upper() if num_fmt == "upperRoman" else roman
    if num_fmt in ("russianLower", "russianUpper"):
        n = len(_RUSSIAN_LETTERS)
        letter = _RUSSIAN_LETTERS[(value - 1) % n] * ((value - 1) // n + 1)
        return letter.upper() if num_fmt == "russianUpper" else letter
    # decimal and anything unknown
    return str(value)


@dataclass(frozen=True)
class _Level:
    num_fmt: str
    lvl_text: str
    start: int


@dataclass(frozen=True)
class _Num:
    abstract_id: int
    start_overrides: dict[int, int]
    level_overrides: dict[int, _Level]


@dataclass
class _NumberingModel:
    """Definitions from word/numbering.xml + paragraph-style numPr from word/styles.xml."""

    abstracts: dict[int, dict[int, _Level]] = field(default_factory=dict)
    nums: dict[int, _Num] = field(default_factory=dict)
    # style_id -> (based_on_style_id | None, (num_id, ilvl) | None)
    styles: dict[str, tuple[str | None, tuple[int, int] | None]] = field(default_factory=dict)

    @classmethod
    def load(cls, data: bytes) -> "_NumberingModel":
        model = cls()
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                names = set(z.namelist())
                if "word/numbering.xml" in names:
                    with z.open("word/numbering.xml") as f:
                        model._load_numbering(etree.parse(f).getroot())
                if "word/styles.xml" in names:
                    with z.open("word/styles.xml") as f:
                        model._load_styles(etree.parse(f).getroot())
        except Exception:
            return cls()
        return model

    def _load_numbering(self, root) -> None:
        for abstract in root.iter(_w("abstractNum")):
            raw_id = abstract.get(_w("abstractNumId"))
            if raw_id is None:
                continue
            levels: dict[int, _Level] = {}
            for lvl in abstract.findall(_w("lvl")):
                parsed = self._parse_level(lvl)
                if parsed is not None:
                    levels[parsed[0]] = parsed[1]
            self.abstracts[int(raw_id)] = levels

        for num in root.iter(_w("num")):
            raw_num_id = num.get(_w("numId"))
            abstract_ref = num.find(_w("abstractNumId"))
            if raw_num_id is None or abstract_ref is None:
                continue
            abstract_val = abstract_ref.get(_w("val"))
            if abstract_val is None:
                continue
            start_overrides: dict[int, int] = {}
            level_overrides: dict[int, _Level] = {}
            for override in num.findall(_w("lvlOverride")):
                raw_ilvl = override.get(_w("ilvl"))
                if raw_ilvl is None:
                    continue
                ilvl = int(raw_ilvl)
                start_override = override.find(_w("startOverride"))
                if start_override is not None and start_override.get(_w("val")) is not None:
                    start_overrides[ilvl] = int(start_override.get(_w("val")))
                lvl = override.find(_w("lvl"))
                if lvl is not None:
                    parsed = self._parse_level(lvl)
                    if parsed is not None:
                        level_overrides[parsed[0]] = parsed[1]
            self.nums[int(raw_num_id)] = _Num(int(abstract_val), start_overrides, level_overrides)

    @staticmethod
    def _parse_level(lvl) -> tuple[int, _Level] | None:
        raw_ilvl = lvl.get(_w("ilvl"))
        if raw_ilvl is None:
            return None
        num_fmt_el = lvl.find(_w("numFmt"))
        lvl_text_el = lvl.find(_w("lvlText"))
        start_el = lvl.find(_w("start"))
        num_fmt = num_fmt_el.get(_w("val")) if num_fmt_el is not None else "decimal"
        lvl_text = lvl_text_el.get(_w("val")) if lvl_text_el is not None else ""
        try:
            start = int(start_el.get(_w("val"))) if start_el is not None else 1
        except (TypeError, ValueError):
            start = 1
        return int(raw_ilvl), _Level(num_fmt or "decimal", lvl_text or "", start)

    def _load_styles(self, root) -> None:
        for style in root.iter(_w("style")):
            style_id = style.get(_w("styleId"))
            if style_id is None:
                continue
            based_on_el = style.find(_w("basedOn"))
            based_on = based_on_el.get(_w("val")) if based_on_el is not None else None
            numpr: tuple[int, int] | None = None
            ppr = style.find(_w("pPr"))
            if ppr is not None:
                num_pr = ppr.find(_w("numPr"))
                if num_pr is not None:
                    num_id_el = num_pr.find(_w("numId"))
                    ilvl_el = num_pr.find(_w("ilvl"))
                    if num_id_el is not None and num_id_el.get(_w("val")) is not None:
                        ilvl = 0
                        if ilvl_el is not None and ilvl_el.get(_w("val")) is not None:
                            ilvl = int(ilvl_el.get(_w("val")))
                        numpr = (int(num_id_el.get(_w("val"))), ilvl)
            self.styles[style_id] = (based_on, numpr)

    def style_numpr(self, style_id: str) -> tuple[int, int] | None:
        seen = 0
        current: str | None = style_id
        while current is not None and seen < _MAX_STYLE_CHAIN:
            entry = self.styles.get(current)
            if entry is None:
                return None
            based_on, numpr = entry
            if numpr is not None:
                return numpr
            current = based_on
            seen += 1
        return None

    def effective_levels(self, num_id: int) -> dict[int, _Level] | None:
        num = self.nums.get(num_id)
        if num is None:
            return None
        base = self.abstracts.get(num.abstract_id)
        if base is None:
            return None
        return {**base, **num.level_overrides}


class NumberingResolver:
    """Resolve a rendered_number string for each top-level paragraph.

    Strategy, in priority order:
    1. "native" — replay Word's numbering model: numbering.xml
       (abstractNum / lvlText / numFmt / start / lvlOverride) plus
       style-based numPr from styles.xml, maintaining per-abstractNum
       level counters in document order. Confidence 0.95; if the paragraph
       text itself starts with a different manual number, confidence drops
       to 0.6 and a NUMBERING_TEXT_MISMATCH diagnostic is emitted.
    2. "regex" — manually typed numbers at the start of the paragraph
       text (confidence 0.7).
    3. "unmapped" — no numbering detected (confidence 0.0).

    Known simplifications (rare in contracts, flagged by confidence
    instead of being modelled): numbered paragraphs inside table cells do
    not advance counters, and w:lvlRestart is not honoured.
    """

    def resolve(self, data: bytes, raw_doc: RawDocument) -> NumberingResolveResult:
        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        model = _NumberingModel.load(data)
        out: dict[str, NumberingData] = {}
        diags: list[ResolverDiagnostic] = []
        # abstract_id -> {ilvl: current counter value}
        counters: dict[int, dict[int, int]] = {}
        # (num_id, ilvl) pairs that already applied their startOverride
        applied_overrides: set[tuple[int, int]] = set()

        for p in para_blocks:
            num_id, ilvl = self._effective_numpr(p, model)
            if p.num_id is not None and p.num_id != 0 and p.num_id not in model.nums:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="UNKNOWN_NUMID",
                    message=f"numId {p.num_id} not found in numbering.xml",
                    block_id=p.block_id,
                ))

            rendered = None
            if num_id is not None:
                rendered = self._advance_and_render(model, counters, applied_overrides, num_id, ilvl)

            typed = REGEX_NUMBER.match(p.text())
            if rendered is not None:
                confidence = 0.95
                if typed and typed.group(1).rstrip(".") != rendered.rstrip("."):
                    confidence = 0.6
                    diags.append(ResolverDiagnostic(
                        level="warning",
                        component="numbering",
                        code="NUMBERING_TEXT_MISMATCH",
                        message=(
                            f"computed number {rendered!r} disagrees with the number "
                            f"typed in the paragraph text ({typed.group(1)!r})"
                        ),
                        block_id=p.block_id,
                    ))
                out[p.block_id] = NumberingData(rendered_number=rendered, confidence=confidence, source="native")
                continue

            if typed:
                num = typed.group(1)
                if not num.endswith("."):
                    num += "."
                out[p.block_id] = NumberingData(rendered_number=num, confidence=0.7, source="regex")
                continue

            out[p.block_id] = NumberingData(rendered_number=None, confidence=0.0, source="unmapped")

        for p in para_blocks:
            nd = out[p.block_id]
            if nd.rendered_number is not None and nd.confidence < LOW_CONFIDENCE_THRESHOLD:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="LOW_CONFIDENCE",
                    message=f"low confidence for paragraph {p.block_id} ({nd.confidence:.2f})",
                    block_id=p.block_id,
                ))
        return out, diags

    def _effective_numpr(self, p: RawParagraph, model: _NumberingModel) -> tuple[int | None, int]:
        if p.num_id is not None:
            # numId 0 is Word's way of saying "numbering removed here".
            if p.num_id == 0:
                return None, 0
            return p.num_id, p.ilvl or 0
        if p.style_id:
            numpr = model.style_numpr(p.style_id)
            if numpr is not None and numpr[0] != 0:
                return numpr
        return None, 0

    def _advance_and_render(
        self,
        model: _NumberingModel,
        counters: dict[int, dict[int, int]],
        applied_overrides: set[tuple[int, int]],
        num_id: int,
        ilvl: int,
    ) -> str | None:
        num = model.nums.get(num_id)
        levels = model.effective_levels(num_id)
        if num is None or levels is None or ilvl not in levels:
            return None
        level = levels[ilvl]
        if level.num_fmt in ("bullet", "none"):
            # Bulleted lists are not clause numbers.
            return None

        c = counters.setdefault(num.abstract_id, {})
        if ilvl in c:
            c[ilvl] += 1
        else:
            c[ilvl] = level.start
        if (num_id, ilvl) not in applied_overrides:
            applied_overrides.add((num_id, ilvl))
            if ilvl in num.start_overrides:
                c[ilvl] = num.start_overrides[ilvl]
        # A new item at this level restarts all deeper levels.
        for deeper in [lv for lv in c if lv > ilvl]:
            del c[deeper]
        # lvlText may reference ancestor levels not seen yet (e.g. "%1.%2.").
        for ancestor in range(ilvl):
            if ancestor not in c and ancestor in levels:
                c[ancestor] = levels[ancestor].start

        def substitute(match: re.Match[str]) -> str:
            ref = int(match.group(1)) - 1
            ref_level = levels.get(ref)
            value = c.get(ref, ref_level.start if ref_level else 1)
            return _format_value(value, ref_level.num_fmt if ref_level else "decimal")

        rendered = _PLACEHOLDER.sub(substitute, level.lvl_text).strip()
        return rendered or None
