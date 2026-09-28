from __future__ import annotations

from dataclasses import replace

from lxml import etree

from app.processing.docx_package import DocxPackage

from app.processing.types import (
    RawDocument,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
    RevisionRecord,
    Run,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


class OOXMLParser:
    def parse(self, data: bytes | DocxPackage) -> RawDocument:
        if not isinstance(data, DocxPackage):
            with DocxPackage(data) as package:
                return self.parse(package)
        root = data.xml("word/document.xml")
        body = root.find(f"{{{W_NS}}}body")
        if body is None:
            raise ValueError("OOXML document.xml does not contain a WordprocessingML body")
        blocks: list = []
        p_idx = 0
        t_idx = 0
        block_idx = 0
        for child in self._iter_block_children(body, data):
            tag = etree.QName(child.tag).localname
            if tag == "p":
                p_idx += 1
                blocks.append(
                    replace(
                        self._parse_paragraph(child, f"p_{p_idx:04d}", is_in_table=False, package=data),
                        block_index=block_idx,
                    )
                )
                block_idx += 1
            elif tag == "tbl":
                t_idx += 1
                blocks.append(self._parse_table(child, f"t_{t_idx:04d}", block_idx, data))
                block_idx += 1
        data.check_budget()
        return RawDocument(blocks=tuple(blocks))

    def _iter_block_children(self, elem, package: DocxPackage):
        for child in package.checked(elem):
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child.tag).localname
            if tag in ("p", "tbl"):
                yield child
            elif tag == "sdt":
                content = child.find(f"{{{W_NS}}}sdtContent")
                if content is not None:
                    yield from self._iter_block_children(content, package)
                elif self._contains_block_children(child):
                    raise ValueError(
                        "w:sdt missing w:sdtContent but contains block-level content"
                    )
            elif self._contains_block_children(child):
                raise ValueError(
                    f"Unsupported OOXML block-level wrapper w:{tag} contains w:p or w:tbl"
                )

    def _contains_block_children(self, elem) -> bool:
        return (
            elem.find(f".//{{{W_NS}}}p") is not None
            or elem.find(f".//{{{W_NS}}}tbl") is not None
        )

    def _parse_paragraph(self, p_elem, block_id: str, is_in_table: bool, package: DocxPackage) -> RawParagraph:
        runs: list[Run] = []
        adjacent_parts: list[str] = []
        previous_style: tuple[bool, bool] | None = None
        for r in package.checked(p_elem.iter(f"{{{W_NS}}}r")):
            text_parts: list[str] = []
            for t in package.checked(r.iter()):
                if not isinstance(t.tag, str):
                    continue
                local = etree.QName(t.tag).localname
                if local in ("t", "delText") and t.text:
                    text_parts.append(t.text)
                elif local == "tab":
                    text_parts.append("\t")
                elif local == "br":
                    text_parts.append("\n")
            txt = "".join(text_parts)
            if not txt:
                continue
            rpr = r.find(f"{{{W_NS}}}rPr")
            bold = rpr is not None and rpr.find(f"{{{W_NS}}}b") is not None
            italic = rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None
            style = (bold, italic)
            if previous_style is not None and style != previous_style:
                runs.append(Run(text="".join(adjacent_parts), bold=previous_style[0], italic=previous_style[1]))
                adjacent_parts = []
            adjacent_parts.append(txt)
            previous_style = style
        if previous_style is not None:
            runs.append(Run(text="".join(adjacent_parts), bold=previous_style[0], italic=previous_style[1]))
        package.check_budget()
        ppr = p_elem.find(f"{{{W_NS}}}pPr")
        num_id = None
        ilvl = None
        style_id = None
        if ppr is not None:
            num_pr = ppr.find(f"{{{W_NS}}}numPr")
            if num_pr is not None:
                ni = num_pr.find(f"{{{W_NS}}}numId")
                il = num_pr.find(f"{{{W_NS}}}ilvl")
                if ni is not None and ni.get(f"{{{W_NS}}}val") is not None:
                    num_id = int(ni.get(f"{{{W_NS}}}val"))
                if il is not None and il.get(f"{{{W_NS}}}val") is not None:
                    ilvl = int(il.get(f"{{{W_NS}}}val"))
            ps = ppr.find(f"{{{W_NS}}}pStyle")
            if ps is not None:
                style_id = ps.get(f"{{{W_NS}}}val")
        return RawParagraph(
            block_id=block_id,
            runs=tuple(runs),
            num_id=num_id,
            ilvl=ilvl,
            style_id=style_id,
            is_in_table=is_in_table,
        )

    def _parse_table(self, tbl_elem, block_id: str, block_index: int, package: DocxPackage) -> RawTable:
        if tbl_elem.find(f".//{{{W_NS}}}cellMerge") is not None:
            raise ValueError(
                "Правки объединения ячеек Word (w:cellMerge) не поддерживаются. "
                "Примите или отклоните эту правку в Word перед загрузкой."
            )
        has_revisions = any(
            tbl_elem.find(f".//{{{W_NS}}}{tag}") is not None
            for tag in ("ins", "del", "moveFrom", "moveTo", "cellIns", "cellDel")
        )
        rows: list[RawTableRow] = []
        cell_p_counter = 0
        for tr in package.checked(tbl_elem.findall(f"{{{W_NS}}}tr")):
            cells: list[RawTableCell] = []
            for tc in package.checked(tr.findall(f"{{{W_NS}}}tc")):
                cell_paragraphs: list[RawParagraph] = []
                for p in self._iter_block_children(tc, package):
                    if etree.QName(p.tag).localname != "p":
                        raise ValueError(
                            "OOXML table cells containing nested w:tbl are not supported"
                        )
                    cell_p_counter += 1
                    cell_pid = f"{block_id}_p_{cell_p_counter:04d}"
                    cell_paragraphs.append(
                        self._parse_paragraph(p, cell_pid, is_in_table=True, package=package)
                    )
                cell_changes = self._structural_changes(tc, "tcPr", "cellIns", "cellDel")
                cells.append(RawTableCell(
                    paragraphs=tuple(cell_paragraphs),
                    exists_in_original=not any(r.type == "INS" for r in cell_changes),
                    exists_in_accepted=not any(r.type == "DEL" for r in cell_changes),
                    revisions=cell_changes,
                ))
            row_changes = self._structural_changes(tr, "trPr", "ins", "del")
            rows.append(RawTableRow(
                cells=tuple(cells),
                exists_in_original=not any(r.type == "INS" for r in row_changes),
                exists_in_accepted=not any(r.type == "DEL" for r in row_changes),
                revisions=row_changes,
            ))
        return RawTable(
            block_id=block_id,
            block_index=block_index,
            rows=tuple(rows),
            has_revisions=has_revisions,
        )

    @staticmethod
    def _structural_changes(elem, properties: str, inserted: str, deleted: str):
        changes = []
        for tag, revision_type in ((inserted, "INS"), (deleted, "DEL")):
            change = elem.find(f"{{{W_NS}}}{properties}/{{{W_NS}}}{tag}")
            if change is not None:
                changes.append(RevisionRecord(
                    type=revision_type, text="", author=change.get(f"{{{W_NS}}}author") or "",
                ))
        if len(changes) > 1:
            raise ValueError("Противоречивые правки вставки и удаления строки или ячейки Word")
        return tuple(changes)
