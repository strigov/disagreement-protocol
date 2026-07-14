from __future__ import annotations

import zipfile
from io import BytesIO

from lxml import etree

from app.processing.types import (
    RawDocument,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
    Run,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


class OOXMLParser:
    def parse(self, data: bytes) -> RawDocument:
        with zipfile.ZipFile(BytesIO(data)) as z:
            with z.open("word/document.xml") as f:
                tree = etree.parse(f)
        body = tree.getroot().find(f"{{{W_NS}}}body")
        if body is None:
            raise ValueError("OOXML document.xml does not contain a WordprocessingML body")
        blocks: list = []
        p_idx = 0
        t_idx = 0
        block_idx = 0
        for child in self._iter_block_children(body):
            tag = etree.QName(child.tag).localname
            if tag == "p":
                p_idx += 1
                blocks.append(
                    self._parse_paragraph(child, f"p_{p_idx:04d}", is_in_table=False)
                )
                block_idx += 1
            elif tag == "tbl":
                t_idx += 1
                blocks.append(self._parse_table(child, f"t_{t_idx:04d}", block_idx))
                block_idx += 1
        return RawDocument(blocks=tuple(blocks))

    def _iter_block_children(self, elem):
        for child in elem:
            tag = etree.QName(child.tag).localname
            if tag in ("p", "tbl"):
                yield child
            elif tag == "sdt":
                content = child.find(f"{{{W_NS}}}sdtContent")
                if content is not None:
                    yield from self._iter_block_children(content)
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

    def _parse_paragraph(self, p_elem, block_id: str, is_in_table: bool) -> RawParagraph:
        runs: list[Run] = []
        for r in p_elem.iter(f"{{{W_NS}}}r"):
            text_parts: list[str] = []
            for t in r.iter():
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
            if runs and runs[-1].bold == bold and runs[-1].italic == italic:
                runs[-1] = Run(text=runs[-1].text + txt, bold=bold, italic=italic)
            else:
                runs.append(Run(text=txt, bold=bold, italic=italic))
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

    def _parse_table(self, tbl_elem, block_id: str, block_index: int) -> RawTable:
        has_revisions = (
            tbl_elem.find(f".//{{{W_NS}}}ins") is not None
            or tbl_elem.find(f".//{{{W_NS}}}del") is not None
        )
        rows: list[RawTableRow] = []
        cell_p_counter = 0
        for tr in tbl_elem.findall(f"{{{W_NS}}}tr"):
            cells: list[RawTableCell] = []
            for tc in tr.findall(f"{{{W_NS}}}tc"):
                cell_paragraphs: list[RawParagraph] = []
                for p in self._iter_block_children(tc):
                    if etree.QName(p.tag).localname != "p":
                        raise ValueError(
                            "OOXML table cells containing nested w:tbl are not supported"
                        )
                    cell_p_counter += 1
                    cell_pid = f"{block_id}_p_{cell_p_counter:04d}"
                    cell_paragraphs.append(
                        self._parse_paragraph(p, cell_pid, is_in_table=True)
                    )
                cells.append(RawTableCell(paragraphs=tuple(cell_paragraphs)))
            rows.append(RawTableRow(cells=tuple(cells)))
        return RawTable(
            block_id=block_id,
            block_index=block_index,
            rows=tuple(rows),
            has_revisions=has_revisions,
        )
