from __future__ import annotations

import zipfile
from io import BytesIO

from lxml import etree

from app.processing.types import (
    RawDocument,
    RawParagraph,
    ResolverDiagnostic,
    RevisionData,
    RevisionRecord,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

RevisionResolveResult = tuple[dict[str, RevisionData], list[ResolverDiagnostic]]


class RevisionResolver:
    """Build original_text / accepted_text for each top-level paragraph."""

    def resolve(self, data: bytes, raw_doc: RawDocument) -> RevisionResolveResult:
        with zipfile.ZipFile(BytesIO(data)) as z:
            with z.open("word/document.xml") as f:
                tree = etree.parse(f)
        body = tree.getroot().find(f"{{{W_NS}}}body")
        out: dict[str, RevisionData] = {}
        diags: list[ResolverDiagnostic] = []
        if body is None:
            return out, diags

        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        body_paragraphs = [
            c
            for c in self._iter_block_children(body)
            if etree.QName(c.tag).localname == "p"
        ]
        for raw_p, p_elem in zip(para_blocks, body_paragraphs):
            rd = self._paragraph_revision(p_elem)
            out[raw_p.block_id] = rd
            if rd.revisions and rd.original_text == rd.accepted_text:
                diags.append(
                    ResolverDiagnostic(
                        level="warning",
                        component="revision",
                        code="FORMAT_ONLY_MISMATCH",
                        message="format-only revisions detected (original==accepted)",
                        block_id=raw_p.block_id,
                    )
                )

        for raw_p in para_blocks[len(body_paragraphs) :]:
            text = raw_p.text()
            out[raw_p.block_id] = RevisionData(
                original_text=text,
                accepted_text=text,
                revisions=(),
            )
        return out, diags

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
        return RevisionData(
            original_text="".join(original_parts),
            accepted_text="".join(accepted_parts),
            revisions=tuple(revisions),
        )
