from __future__ import annotations

import zipfile
from io import BytesIO

from lxml import etree

from app.processing.types import (
    RawDocument,
    RawParagraph,
    RawTable,
    ResolverDiagnostic,
    RevisionData,
    RevisionRecord,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

RevisionResolveResult = tuple[dict[str, RevisionData], list[ResolverDiagnostic]]


class RevisionResolver:
    """Build original_text / accepted_text for document and table paragraphs."""

    def resolve(self, data: bytes, raw_doc: RawDocument) -> RevisionResolveResult:
        with zipfile.ZipFile(BytesIO(data)) as z:
            with z.open("word/document.xml") as f:
                tree = etree.parse(f)
        body = tree.getroot().find(f"{{{W_NS}}}body")
        out: dict[str, RevisionData] = {}
        diags: list[ResolverDiagnostic] = []
        if body is None:
            return out, diags

        body_blocks = list(self._iter_block_children(body))
        xml_index = 0
        for raw_block in raw_doc.blocks:
            expected_tag = "p" if isinstance(raw_block, RawParagraph) else "tbl"
            xml_block = body_blocks[xml_index] if xml_index < len(body_blocks) else None
            if xml_block is not None and etree.QName(xml_block.tag).localname == expected_tag:
                xml_index += 1
                if isinstance(raw_block, RawParagraph):
                    self._store_paragraph_revision(
                        raw_block,
                        self._paragraph_revision(xml_block),
                        out,
                        diags,
                    )
                else:
                    self._resolve_table(raw_block, xml_block, out, diags)
                continue

            if isinstance(raw_block, RawParagraph):
                self._store_paragraph_revision(raw_block, self._plain_revision(raw_block), out, diags)
            else:
                self._resolve_table(raw_block, None, out, diags)
        return out, diags

    def _plain_revision(self, raw_p: RawParagraph) -> RevisionData:
        text = raw_p.text()
        return RevisionData(original_text=text, accepted_text=text, revisions=())

    def _store_paragraph_revision(
        self,
        raw_p: RawParagraph,
        revision_data: RevisionData,
        out: dict[str, RevisionData],
        diags: list[ResolverDiagnostic],
    ) -> None:
        out[raw_p.block_id] = revision_data
        if revision_data.revisions and revision_data.original_text == revision_data.accepted_text:
            diags.append(
                ResolverDiagnostic(
                    level="warning",
                    component="revision",
                    code="FORMAT_ONLY_MISMATCH",
                    message="Обнаружена форматная правка без изменения текста",
                    block_id=raw_p.block_id,
                )
            )

    def _resolve_table(
        self,
        raw_table: RawTable,
        tbl_elem,
        out: dict[str, RevisionData],
        diags: list[ResolverDiagnostic],
    ) -> None:
        xml_rows = tbl_elem.findall(f"{{{W_NS}}}tr") if tbl_elem is not None else []
        for row_index, raw_row in enumerate(raw_table.rows):
            xml_row = xml_rows[row_index] if row_index < len(xml_rows) else None
            xml_cells = (
                xml_row.findall(f"{{{W_NS}}}tc") if xml_row is not None else []
            )
            for cell_index, raw_cell in enumerate(raw_row.cells):
                xml_cell = xml_cells[cell_index] if cell_index < len(xml_cells) else None
                xml_paragraphs = []
                if xml_cell is not None:
                    xml_paragraphs = [
                        block
                        for block in self._iter_block_children(xml_cell)
                        if etree.QName(block.tag).localname == "p"
                    ]
                for paragraph_index, raw_p in enumerate(raw_cell.paragraphs):
                    if paragraph_index < len(xml_paragraphs):
                        revision_data = self._paragraph_revision(xml_paragraphs[paragraph_index])
                    else:
                        revision_data = self._plain_revision(raw_p)
                    self._store_paragraph_revision(raw_p, revision_data, out, diags)

    def _iter_block_children(self, elem):
        for child in elem:
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child.tag).localname
            if tag in ("p", "tbl"):
                yield child
            elif tag == "sdt":
                content = child.find(f"{{{W_NS}}}sdtContent")
                if content is not None:
                    yield from self._iter_block_children(content)

    def _paragraph_revision(self, p_elem) -> RevisionData:
        original_parts: list[str] = []
        accepted_parts: list[str] = []
        revisions: list[RevisionRecord] = []

        def walk(elem, revision_stack: list[str]) -> None:
            if not isinstance(elem.tag, str):
                return
            local = etree.QName(elem.tag).localname
            if local in ("ins", "del"):
                is_top_level = not revision_stack
                author = elem.get(f"{{{W_NS}}}author") or ""
                original_start = len(original_parts)
                accepted_start = len(accepted_parts)
                revision_stack.append(local)
                for child in elem:
                    walk(child, revision_stack)
                revision_stack.pop()
                if is_top_level:
                    if local == "ins":
                        ins_text = "".join(accepted_parts[accepted_start:])
                        if ins_text:
                            revisions.append(
                                RevisionRecord(
                                    type="INS",
                                    text=ins_text,
                                    author=author,
                                )
                            )
                    else:
                        del_text = "".join(original_parts[original_start:])
                        if del_text:
                            revisions.append(
                                RevisionRecord(
                                    type="DEL",
                                    text=del_text,
                                    author=author,
                                )
                            )
                return

            top_context = revision_stack[0] if revision_stack else None
            nested_context = revision_stack[1:]
            if local in ("tab", "br"):
                text = "\t" if local == "tab" else "\n"
                if top_context is None:
                    original_parts.append(text)
                    accepted_parts.append(text)
                elif top_context == "ins" and "del" not in nested_context:
                    accepted_parts.append(text)
                elif top_context == "del" and "ins" not in nested_context:
                    original_parts.append(text)
            if local == "t" and elem.text:
                if top_context is None:
                    original_parts.append(elem.text)
                    accepted_parts.append(elem.text)
                elif top_context == "ins" and "del" not in nested_context:
                    accepted_parts.append(elem.text)
            elif (
                local == "delText"
                and elem.text
                and top_context == "del"
                and "ins" not in nested_context
            ):
                original_parts.append(elem.text)

            for child in elem:
                walk(child, revision_stack)

        walk(p_elem, [])
        original_text = "".join(original_parts)
        accepted_text = "".join(accepted_parts)

        if original_text.strip() == "":
            if accepted_text.strip() != "":
                exists_in_original = False
            else:
                ppr = p_elem.find(f"{{{W_NS}}}pPr")
                rpr = ppr.find(f"{{{W_NS}}}rPr") if ppr is not None else None
                has_inserted_mark = rpr is not None and rpr.find(f"{{{W_NS}}}ins") is not None
                has_deleted_mark = rpr is not None and rpr.find(f"{{{W_NS}}}del") is not None
                exists_in_original = not has_inserted_mark or has_deleted_mark
        else:
            exists_in_original = True

        original_style_id = None
        original_num_id = None
        original_ilvl = None
        original_numpr_present = False
        ppr = p_elem.find(f"{{{W_NS}}}pPr")
        ppr_change = ppr.find(f"{{{W_NS}}}pPrChange") if ppr is not None else None
        original_ppr = (
            ppr_change.find(f"{{{W_NS}}}pPr")
            if ppr_change is not None
            else None
        )
        original_ppr_change = ppr_change is not None
        if original_ppr is not None:
            original_style = original_ppr.find(f"{{{W_NS}}}pStyle")
            if original_style is not None:
                original_style_id = original_style.get(f"{{{W_NS}}}val")
            original_numpr = original_ppr.find(f"{{{W_NS}}}numPr")
            if original_numpr is not None:
                original_numpr_present = True
                original_num_id_element = original_numpr.find(f"{{{W_NS}}}numId")
                if (
                    original_num_id_element is not None
                    and original_num_id_element.get(f"{{{W_NS}}}val") is not None
                ):
                    try:
                        original_num_id = int(
                            original_num_id_element.get(f"{{{W_NS}}}val")
                        )
                    except (TypeError, ValueError):
                        original_num_id = None
                original_ilvl = 0
                original_ilvl_element = original_numpr.find(f"{{{W_NS}}}ilvl")
                if (
                    original_ilvl_element is not None
                    and original_ilvl_element.get(f"{{{W_NS}}}val") is not None
                ):
                    try:
                        original_ilvl = int(
                            original_ilvl_element.get(f"{{{W_NS}}}val")
                        )
                    except (TypeError, ValueError):
                        original_ilvl = None

        def run_text(run_elem) -> str:
            parts: list[str] = []
            for node in run_elem.iter():
                if not isinstance(node.tag, str):
                    continue
                local = etree.QName(node.tag).localname
                if local in ("t", "delText") and node.text:
                    parts.append(node.text)
                elif local == "tab":
                    parts.append("\t")
                elif local == "br":
                    parts.append("\n")
            return "".join(parts)

        def containing_run(change_elem):
            ancestor = change_elem.getparent()
            while ancestor is not None:
                if isinstance(ancestor.tag, str) and etree.QName(ancestor.tag).localname == "r":
                    return ancestor
                ancestor = ancestor.getparent()
            return None

        run_text_cache: dict[object, str] = {}
        for change_elem in p_elem.iter():
            if not isinstance(change_elem.tag, str):
                continue
            local = etree.QName(change_elem.tag).localname
            if local == "rPrChange":
                run_elem = containing_run(change_elem)
                if run_elem is None:
                    text = ""
                else:
                    if run_elem not in run_text_cache:
                        run_text_cache[run_elem] = run_text(run_elem)
                    text = run_text_cache[run_elem]
                text = text or accepted_text
            elif local == "pPrChange":
                text = accepted_text
            else:
                continue
            revisions.append(
                RevisionRecord(
                    type="FORMAT_ONLY",
                    text=text,
                    author=change_elem.get(f"{{{W_NS}}}author") or "",
                ),
            )

        return RevisionData(
            original_text=original_text,
            accepted_text=accepted_text,
            revisions=tuple(revisions),
            exists_in_original=exists_in_original,
            original_style_id=original_style_id,
            original_num_id=original_num_id,
            original_ilvl=original_ilvl,
            original_numpr_present=original_numpr_present,
            original_ppr_change=original_ppr_change,
        )
