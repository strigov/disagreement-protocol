from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO

from lxml import etree

from app.processing.types import (
    NumberingData,
    RawDocument,
    RawParagraph,
    ResolverDiagnostic,
    RevisionData,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REGEX_NUMBER = re.compile(r"^\s*(?:Статья\s+)?(\d+(?:\.\d+)*\.?)\s+", re.IGNORECASE)
LOW_CONFIDENCE_THRESHOLD = 0.85
_PLACEHOLDER = re.compile(r"%(\d)")
_MAX_STYLE_CHAIN = 10
_MAX_WORD_LEVEL = 8
_MAX_NUMBERING_START = 100_000
_MAX_DERIVED_COUNTER = _MAX_NUMBERING_START
_MAX_RENDERED_NUMBER_CHARS = 4_096
_MAX_DOCUMENT_RENDERED_CHARS = 1_000_000
_MAX_DIAGNOSTIC_NUMBER_CHARS = 256
_MAX_LVL_TEXT_SOURCE_CHARS = 65_536
_MAX_NUMBERING_XML_BYTES = 5_000_000
_MAX_STYLES_XML_BYTES = 5_000_000

_ROMAN = (
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
    (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
)
# Word's russian numbering alphabet: no ё, й, ъ, ы, ь.
_RUSSIAN_LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"

NumberingResolveResult = tuple[dict[str, NumberingData], list[ResolverDiagnostic]]


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _bounded_int(raw: str | int | None, lower: int, upper: int) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if lower <= value <= upper else None


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
                    info = z.getinfo("word/numbering.xml")
                    if info.file_size <= _MAX_NUMBERING_XML_BYTES:
                        with z.open(info) as f:
                            model._load_numbering(etree.parse(f).getroot())
                if "word/styles.xml" in names:
                    info = z.getinfo("word/styles.xml")
                    if info.file_size <= _MAX_STYLES_XML_BYTES:
                        with z.open(info) as f:
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
                ilvl = _bounded_int(raw_ilvl, 0, _MAX_WORD_LEVEL)
                if ilvl is None:
                    continue
                start_override = override.find(_w("startOverride"))
                if start_override is not None and start_override.get(_w("val")) is not None:
                    start = _bounded_int(
                        start_override.get(_w("val")),
                        1,
                        _MAX_NUMBERING_START,
                    )
                    if start is not None:
                        start_overrides[ilvl] = start
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
        ilvl = _bounded_int(raw_ilvl, 0, _MAX_WORD_LEVEL)
        if ilvl is None:
            return None
        num_fmt_el = lvl.find(_w("numFmt"))
        lvl_text_el = lvl.find(_w("lvlText"))
        start_el = lvl.find(_w("start"))
        num_fmt = num_fmt_el.get(_w("val")) if num_fmt_el is not None else "decimal"
        lvl_text = lvl_text_el.get(_w("val")) if lvl_text_el is not None else ""
        start = (
            _bounded_int(start_el.get(_w("val")), 1, _MAX_NUMBERING_START)
            if start_el is not None
            else None
        )
        return ilvl, _Level(num_fmt or "decimal", lvl_text or "", start or 1)

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
                            parsed_ilvl = _bounded_int(
                                ilvl_el.get(_w("val")),
                                0,
                                _MAX_WORD_LEVEL,
                            )
                            if parsed_ilvl is None:
                                continue
                            ilvl = parsed_ilvl
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

    def resolve(
        self,
        data: bytes,
        raw_doc: RawDocument,
        revision_map: dict[str, RevisionData],
    ) -> NumberingResolveResult:
        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        model = _NumberingModel.load(data)
        out: dict[str, NumberingData] = {}
        diags: list[ResolverDiagnostic] = []
        # abstract_id -> {ilvl: current counter value}
        counters: dict[int, dict[int, int]] = {}
        # (num_id, ilvl) pairs that already applied their startOverride
        applied_overrides: set[tuple[int, int]] = set()
        rendered_chars = 0

        for p in para_blocks:
            revision = revision_map.get(p.block_id)
            num_id, ilvl = self._effective_numpr(p, model, revision)
            if num_id is not None and num_id != 0 and num_id not in model.nums:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="UNKNOWN_NUMID",
                    message=f"numId {p.num_id} отсутствует в numbering.xml",
                    block_id=p.block_id,
                ))

            exists_in_original = revision.exists_in_original if revision is not None else True
            numbering_text = (
                revision.original_text
                if exists_in_original and revision is not None
                else revision.accepted_text
                if revision is not None
                else p.text()
            )
            native_level = self._native_level(model, num_id, ilvl)
            structural_level = ilvl if num_id is not None else None

            if native_level is not None:
                if exists_in_original:
                    rendered, rendered_chars = self._advance_and_render(
                        model,
                        counters,
                        applied_overrides,
                        num_id,
                        ilvl,
                        rendered_chars,
                    )
                else:
                    rendered = None
                if rendered is not None:
                    confidence = 0.95
                    typed = REGEX_NUMBER.match(numbering_text)
                    if typed:
                        typed_length = typed.end(1) - typed.start(1)
                        if typed_length > _MAX_DIAGNOSTIC_NUMBER_CHARS:
                            typed_display = f"<номер длиной {typed_length} символов>"
                            mismatch = True
                        else:
                            typed_value = typed.group(1)
                            typed_display = repr(typed_value)
                            mismatch = typed_value.rstrip(".") != rendered.rstrip(".")
                    else:
                        typed_display = ""
                        mismatch = False
                    if mismatch:
                        confidence = 0.6
                        diags.append(ResolverDiagnostic(
                            level="warning",
                            component="numbering",
                            code="NUMBERING_TEXT_MISMATCH",
                            message=(
                                f"Вычисленный номер {rendered!r} не совпадает с номером "
                                f"в тексте абзаца ({typed_display})"
                            ),
                            block_id=p.block_id,
                        ))
                    out[p.block_id] = NumberingData(
                        rendered_number=rendered,
                        confidence=confidence,
                        source="native",
                        numbering_level=structural_level,
                    )
                    continue
                if not exists_in_original:
                    out[p.block_id] = NumberingData(
                        rendered_number=None,
                        confidence=0.95,
                        source="native",
                        numbering_level=structural_level,
                    )
                    continue
                out[p.block_id] = NumberingData(
                    rendered_number=None,
                    confidence=0.95,
                    source="native",
                    numbering_level=structural_level,
                )
                continue

            typed = REGEX_NUMBER.match(numbering_text)
            if typed:
                typed_end = typed.end(1)
                typed_length = typed_end - typed.start(1)
                number_length = typed_length + (0 if numbering_text[typed_end - 1] == "." else 1)
                capture_allowed = number_length <= _MAX_RENDERED_NUMBER_CHARS and (
                    not exists_in_original
                    or number_length <= _MAX_DOCUMENT_RENDERED_CHARS - rendered_chars
                )
                if capture_allowed:
                    num = typed.group(1)
                    if not num.endswith("."):
                        num += "."
                    numbering_level = self._regex_level(typed)
                else:
                    num = None
                    numbering_level = None
                out[p.block_id] = NumberingData(
                    rendered_number=None if not exists_in_original else num,
                    confidence=0.7,
                    source="regex",
                    numbering_level=numbering_level,
                )
                if exists_in_original and num is not None:
                    rendered_chars += len(num)
                continue

            out[p.block_id] = NumberingData(
                rendered_number=None,
                confidence=0.0,
                source="unmapped",
                numbering_level=structural_level,
            )

        for p in para_blocks:
            nd = out[p.block_id]
            if (
                nd.source == "native"
                and nd.rendered_number is not None
                and nd.confidence < LOW_CONFIDENCE_THRESHOLD
            ):
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="LOW_CONFIDENCE",
                    message=(
                        f"Низкая уверенность нумерации для абзаца {p.block_id} "
                        f"({nd.confidence:.2f})"
                    ),
                    block_id=p.block_id,
                ))
        return out, diags

    @staticmethod
    def _native_level(model: _NumberingModel, num_id: int | None, ilvl: int):
        if num_id is None:
            return None
        levels = model.effective_levels(num_id)
        level = levels.get(ilvl) if levels is not None else None
        if level is None or level.num_fmt in ("bullet", "none"):
            return None
        return level

    @staticmethod
    def _regex_level(match: re.Match[str]) -> int:
        return len(match.group(1).rstrip(".").split(".")) - 1

    def _effective_numpr(
        self,
        p: RawParagraph,
        model: _NumberingModel,
        revision: RevisionData | None = None,
    ) -> tuple[int | None, int]:
        if revision is not None and revision.exists_in_original and revision.original_ppr_change:
            if revision.original_numpr_present:
                if revision.original_num_id is None or revision.original_num_id == 0:
                    return None, 0
                if revision.original_ilvl is not None and not 0 <= revision.original_ilvl <= _MAX_WORD_LEVEL:
                    return None, 0
                return revision.original_num_id, revision.original_ilvl or 0
            if revision.original_style_id:
                numpr = model.style_numpr(revision.original_style_id)
                if numpr is not None and numpr[0] != 0:
                    return numpr
            return None, 0
        if p.num_id is not None:
            # numId 0 is Word's way of saying "numbering removed here".
            if p.num_id == 0:
                return None, 0
            if p.ilvl is not None and not 0 <= p.ilvl <= _MAX_WORD_LEVEL:
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
        rendered_chars: int,
    ) -> tuple[str | None, int]:
        num = model.nums.get(num_id)
        levels = model.effective_levels(num_id)
        if num is None or levels is None or ilvl not in levels:
            return None, rendered_chars
        level = levels[ilvl]
        if level.num_fmt in ("bullet", "none"):
            # Bulleted lists are not clause numbers.
            return None, rendered_chars
        if rendered_chars >= _MAX_DOCUMENT_RENDERED_CHARS:
            return None, rendered_chars

        c = counters.setdefault(num.abstract_id, {})
        if ilvl in c:
            counter = c[ilvl] + 1
        else:
            counter = level.start
        if (num_id, ilvl) not in applied_overrides:
            applied_overrides.add((num_id, ilvl))
            if ilvl in num.start_overrides:
                counter = num.start_overrides[ilvl]
        if counter > _MAX_DERIVED_COUNTER:
            c[ilvl] = _MAX_DERIVED_COUNTER + 1
            return None, rendered_chars
        c[ilvl] = counter
        # A new item at this level restarts all deeper levels.
        for deeper in [lv for lv in c if lv > ilvl]:
            del c[deeper]
        # lvlText may reference ancestor levels not seen yet (e.g. "%1.%2.").
        for ancestor in range(ilvl):
            if ancestor not in c and ancestor in levels:
                c[ancestor] = levels[ancestor].start

        remaining_chars = min(
            _MAX_RENDERED_NUMBER_CHARS,
            _MAX_DOCUMENT_RENDERED_CHARS - rendered_chars,
        )
        rendered = self._render_level_text(levels, c, level.lvl_text, remaining_chars)
        if rendered is None:
            return None, rendered_chars
        return rendered, rendered_chars + len(rendered)

    @staticmethod
    def _render_level_text(
        levels: dict[int, _Level],
        counters: dict[int, int],
        lvl_text: str,
        budget: int,
    ) -> str | None:
        if len(lvl_text) > _MAX_LVL_TEXT_SOURCE_CHARS:
            return None
        parts: list[str] = []
        output_length = 0
        last_end = 0
        for match in _PLACEHOLDER.finditer(lvl_text):
            literal_length = match.start() - last_end
            if output_length + literal_length > budget:
                return None
            if literal_length:
                parts.append(lvl_text[last_end:match.start()])
                output_length += literal_length

            ref = int(match.group(1)) - 1
            ref_level = levels.get(ref)
            value = counters.get(ref, ref_level.start if ref_level else 1)
            if value > _MAX_DERIVED_COUNTER:
                return None
            formatted = _format_value(value, ref_level.num_fmt if ref_level else "decimal")
            if output_length + len(formatted) > budget:
                return None
            parts.append(formatted)
            output_length += len(formatted)
            last_end = match.end()

        tail_length = len(lvl_text) - last_end
        if output_length + tail_length > budget:
            return None
        if tail_length:
            parts.append(lvl_text[last_end:])
        rendered = "".join(parts).strip()
        return rendered or None
