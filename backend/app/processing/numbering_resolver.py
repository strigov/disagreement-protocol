from __future__ import annotations
import re
import zipfile
from io import BytesIO
from lxml import etree

from app.processing.types import (
    NumberingData, RawDocument, RawParagraph, ResolverDiagnostic,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REGEX_NUMBER = re.compile(r"^\s*(?:Статья\s+)?(\d+(?:\.\d+)*\.?)\s+", re.IGNORECASE)
LOW_CONFIDENCE_THRESHOLD = 0.85

NumberingResolveResult = tuple[dict[str, NumberingData], list[ResolverDiagnostic]]


class NumberingResolver:
    """Resolve a rendered_number string for each paragraph.

    v1 strategy: try docx2python; on miss, fall back to regex on paragraph text.
    Returns (mapping, diagnostics) where diagnostics flag missing numIds and
    paragraphs whose numbering confidence is below the 0.85 threshold.
    """

    def resolve(self, data: bytes, raw_doc: RawDocument) -> NumberingResolveResult:
        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        d2p_numbers = self._docx2python_numbers(data, len(para_blocks))
        known_num_ids = self._known_num_ids(data)
        out: dict[str, NumberingData] = {}
        diags: list[ResolverDiagnostic] = []
        counters: dict[int, int] = {}
        for idx, p in enumerate(para_blocks):
            if p.num_id is not None and p.num_id not in known_num_ids:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="UNKNOWN_NUMID",
                    message=f"numId {p.num_id} not found in numbering.xml",
                    block_id=p.block_id,
                ))
            d2p = d2p_numbers.get(idx)
            if d2p:
                out[p.block_id] = NumberingData(rendered_number=d2p, confidence=1.0, source="docx2python")
                continue
            m = REGEX_NUMBER.match(p.text())
            if m:
                num = m.group(1)
                if not num.endswith("."):
                    num += "."
                out[p.block_id] = NumberingData(rendered_number=num, confidence=0.7, source="regex")
                continue
            if p.num_id is not None:
                lvl = (p.ilvl or 0) + 1
                counters[lvl] = counters.get(lvl, 0) + 1
                for higher in list(counters):
                    if higher > lvl:
                        del counters[higher]
                rendered = ".".join(str(counters.get(i, 1)) for i in range(1, lvl + 1)) + "."
                out[p.block_id] = NumberingData(rendered_number=rendered, confidence=0.5, source="regex")
            else:
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

    def _known_num_ids(self, data: bytes) -> set[int]:
        """Read numbering.xml and return the set of numId values defined there."""
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                if "word/numbering.xml" not in z.namelist():
                    return set()
                with z.open("word/numbering.xml") as f:
                    tree = etree.parse(f)
        except Exception:
            return set()
        out: set[int] = set()
        for num in tree.getroot().iter(f"{{{W_NS}}}num"):
            val = num.get(f"{{{W_NS}}}numId")
            if val is not None:
                try:
                    out.add(int(val))
                except ValueError:
                    pass
        return out

    def _docx2python_numbers(self, data: bytes, expected: int) -> dict[int, str]:
        """Best-effort docx2python integration. Returns {paragraph_index: rendered_number}.

        If docx2python is not callable on this content, returns {}.
        """
        try:
            from docx2python import docx2python  # type: ignore
        except Exception:
            return {}
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                names = z.namelist()
            if "word/numbering.xml" not in names:
                return {}
            result = docx2python(BytesIO(data), html=False)
            numbers: dict[int, str] = {}
            idx = 0
            for section in result.body:
                for table in section:
                    for row in table:
                        for para in row:
                            if isinstance(para, str) and para.strip():
                                m = re.match(r"^\s*(\d+(?:\.\d+)*\.?)\s+", para)
                                if m:
                                    numbers[idx] = m.group(1) if m.group(1).endswith(".") else m.group(1) + "."
                                idx += 1
                                if idx >= expected:
                                    return numbers
            return numbers
        except Exception:
            return {}
