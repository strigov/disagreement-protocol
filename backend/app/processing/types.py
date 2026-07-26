from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ResolverDiagnostic:
    """Diagnostic emitted by a pipeline resolver/segmenter for the preflight report.

    Components: "numbering" | "revision" | "segmenter".

    The `code` field is the stable machine-readable classifier the
    ValidationEngine routes on. Without it, mapping diagnostics by
    `component` alone produces false positives — e.g. a benign
    format-only-revision diagnostic from the revision resolver would be
    surfaced to the user as a REVISION_MAPPING_MISMATCH warning. Defined
    codes (extend as new diagnostics are added):
      - "UNKNOWN_NUMID"        — numId on a paragraph not present in numbering.xml
      - "LOW_CONFIDENCE"       — numbering.confidence < 0.85
      - "NUMBERING_TEXT_MISMATCH" — computed number differs from the manual
        number typed at the start of the paragraph text
      - "FORMAT_ONLY_MISMATCH" — format-only revisions exist and
        original_text==accepted_text; each w:rPrChange/w:pPrChange is one
        RevisionRecord(type="FORMAT_ONLY") and is counted without making a
        clause changed by itself
      - "MAPPING_MISMATCH"     — generic resolver could not map a block
    """

    level: Literal["warning", "error"]
    component: str
    code: str
    message: str
    block_id: str | None = None


@dataclass(frozen=True)
class Run:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class RawParagraph:
    block_id: str
    runs: tuple[Run, ...]
    num_id: int | None
    ilvl: int | None
    style_id: str | None
    is_in_table: bool = False

    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass(frozen=True)
class RawTableCell:
    paragraphs: tuple["RawParagraph", ...]

    def text(self) -> str:
        return " ".join(p.text() for p in self.paragraphs).strip()


@dataclass(frozen=True)
class RawTableRow:
    cells: tuple[RawTableCell, ...]


@dataclass(frozen=True)
class RawTable:
    block_id: str
    block_index: int
    rows: tuple[RawTableRow, ...]
    has_revisions: bool

    def cell_text(self) -> str:
        """Flattened text of all cells: joined by ' | ' across cells, '\n' across rows."""
        return "\n".join(" | ".join(c.text() for c in r.cells) for r in self.rows)


@dataclass(frozen=True)
class RawDocument:
    blocks: tuple  # tuple[RawParagraph | RawTable, ...]


@dataclass(frozen=True)
class RevisionRecord:
    type: str  # "INS" | "DEL" | "FORMAT_ONLY"
    text: str
    author: str = ""


@dataclass(frozen=True)
class RevisionData:
    original_text: str
    accepted_text: str
    revisions: tuple[RevisionRecord, ...]


@dataclass(frozen=True)
class NumberingData:
    rendered_number: str | None
    confidence: float
    source: str  # "native" | "regex" | "unmapped"


@dataclass(frozen=True)
class EnrichedParagraph:
    block_id: str
    text_runs: str
    num_id: int | None
    ilvl: int | None
    original_text: str
    accepted_text: str
    revisions: tuple[RevisionRecord, ...]
    rendered_number: str | None
    numbering_confidence: float


@dataclass
class Clause:
    clause_key: str
    label: str
    level: int
    parent_key: str | None
    paragraphs: list[EnrichedParagraph] = field(default_factory=list)
    tables: list[RawTable] = field(default_factory=list)
    children: list["Clause"] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
