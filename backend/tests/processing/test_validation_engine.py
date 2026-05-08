from app.processing.types import EnrichedParagraph, Clause, RevisionRecord, ResolverDiagnostic
from app.processing.validation_engine import ValidationEngine
from app.services.protocol_generator import BuiltRow


def _ep(rev_types: list[str], num_conf: float = 1.0) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id="p_0001",
        text_runs="x",
        num_id=1,
        ilvl=0,
        original_text="x",
        accepted_text="x",
        revisions=tuple(RevisionRecord(type=t, text="x") for t in rev_types),
        rendered_number="1.",
        numbering_confidence=num_conf,
    )


def _clause(p, flags=None):
    c = Clause(clause_key="c_p_0001", label="1.", level=0, parent_key=None)
    c.paragraphs.append(p)
    if flags:
        c.flags.update(flags)
    return c


def _row(point_label="1.", flags=None, confidence=0.95, row_id=None):
    return BuiltRow(
        point_label=point_label,
        party_1_text="x",
        party_2_text="x",
        agreed_text="x",
        source_clause_key="c_p_0001",
        confidence=confidence,
        flags=list(flags or []),
        row_id=row_id,
    )


def test_counts_textual_and_format_revisions():
    p = _ep(["INS", "DEL", "FORMAT_ONLY"])
    rep = ValidationEngine().validate([_row()], [_clause(p)], [])
    assert rep.textual_revisions_total == 2
    assert rep.format_only_revisions == 1


def test_empty_protocol_warning_when_no_rows():
    rep = ValidationEngine().validate([], [], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "EMPTY_PROTOCOL" in kinds


def test_low_numbering_confidence_overall():
    p = _ep(["INS"], num_conf=0.0)
    rep = ValidationEngine().validate([_row()], [_clause(p)], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "LOW_NUMBERING_CONFIDENCE_OVERALL" in kinds


def test_multi_paragraph_clause_emits_warning():
    p1 = _ep(["INS"])
    p2 = _ep([])
    c = _clause(p1, flags={"MULTI_PARAGRAPH"})
    c.paragraphs.append(p2)
    rep = ValidationEngine().validate([_row(confidence=0.7)], [c], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "MULTI_PARAGRAPH" in kinds


def test_unknown_numid_diagnostic_produces_numbering_mismatch_warning():
    """A `ResolverDiagnostic` with code="UNKNOWN_NUMID" from the numbering
    resolver becomes a NUMBERING_MAPPING_MISMATCH warning in the report."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="numbering",
        code="UNKNOWN_NUMID",
        message="numId 999 not found in numbering.xml",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    num_warnings = [w for w in rep.warnings if w["kind"] == "NUMBERING_MAPPING_MISMATCH"]
    assert len(num_warnings) == 1
    assert num_warnings[0]["scope"] == "session"


def test_low_confidence_diagnostic_produces_low_numbering_confidence_warning():
    """A `ResolverDiagnostic` with code="LOW_CONFIDENCE" becomes a
    LOW_NUMBERING_CONFIDENCE warning, not NUMBERING_MAPPING_MISMATCH."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="numbering",
        code="LOW_CONFIDENCE",
        message="low confidence for paragraph p_0001 (0.70)",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    kinds = [w["kind"] for w in rep.warnings]
    assert "LOW_NUMBERING_CONFIDENCE" in kinds
    assert "NUMBERING_MAPPING_MISMATCH" not in kinds


def test_format_only_mismatch_diagnostic_does_not_produce_warning():
    """A `ResolverDiagnostic` with code="FORMAT_ONLY_MISMATCH" is expected
    behaviour (revisions exist but the accepted text equals the original);
    it must NOT surface as a REVISION_MAPPING_MISMATCH warning."""
    p = _ep(["FORMAT_ONLY"])
    diag = ResolverDiagnostic(
        level="warning",
        component="revision",
        code="FORMAT_ONLY_MISMATCH",
        message="format-only revisions detected (original==accepted)",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    kinds = [w["kind"] for w in rep.warnings]
    assert "REVISION_MAPPING_MISMATCH" not in kinds


def test_mapping_mismatch_diagnostic_produces_revision_mismatch_warning():
    """A `ResolverDiagnostic` with code="MAPPING_MISMATCH" from the
    revision resolver becomes a REVISION_MAPPING_MISMATCH warning."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="revision",
        code="MAPPING_MISMATCH",
        message="rev id 42 references unknown anchor",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    rev_warnings = [w for w in rep.warnings if w["kind"] == "REVISION_MAPPING_MISMATCH"]
    assert len(rev_warnings) == 1
    assert rev_warnings[0]["scope"] == "session"
    assert "rev id 42" in rev_warnings[0]["message"]


def test_validate_uses_all_clauses_not_just_changed():
    """A format-only revision sitting on an unchanged clause must still be
    counted in `format_only_revisions` because the engine receives ALL
    clauses (not just the changed subset)."""
    changed_p = _ep(["INS"])
    unchanged_p = _ep(["FORMAT_ONLY"])
    rep = ValidationEngine().validate(
        [_row()],
        [_clause(changed_p), _clause(unchanged_p)],
        [],
    )
    assert rep.textual_revisions_total == 1
    assert rep.format_only_revisions == 1


def test_table_cell_change_emits_row_level_warning():
    """Each protocol row carrying the TABLE_CELL_CHANGE flag emits a
    row-level TABLE_CELL_CHANGE warning with the row_id populated, so the
    UI can link the warning back to the offending row."""
    p = _ep(["INS"])
    row = _row(point_label="3.", flags=["TABLE_CELL_CHANGE"], row_id="row_abc")
    rep = ValidationEngine().validate([row], [_clause(p)], [])
    table_warnings = [w for w in rep.warnings if w["kind"] == "TABLE_CELL_CHANGE"]
    assert len(table_warnings) == 1
    assert table_warnings[0]["scope"] == "row"
    assert table_warnings[0]["row_id"] == "row_abc"
    assert "Таблица в пункте 3." in table_warnings[0]["message"]
