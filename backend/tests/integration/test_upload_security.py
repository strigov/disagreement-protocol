import struct
import subprocess
import sys
import zipfile
import zlib
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.request_guard import LocalRequestGuard
from app.main import app
from app.models.document import Document
from app.processing.docx_package import DocxPackage, MAX_FILE_BYTES, PackageError
from app.processing.numbering_resolver import NumberingResolver
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import RawDocument
from app.services.ingestion import IngestError, run_pipeline, validate_upload
from tests.integration.test_review_fixes import W, docx, paragraph

XML = f'<w:document xmlns:w="{W}"><w:body>{paragraph("1. Условие")}</w:body></w:document>'.encode()


def package(xml=XML, extras=(), compression=zipfile.ZIP_DEFLATED):
    out = BytesIO()
    with zipfile.ZipFile(out, "w", compression) as archive:
        archive.writestr("word/document.xml", xml)
        for name, content in extras:
            archive.writestr(name, content)
    return out.getvalue()


ENTRY_POINTS = [
    lambda data: OOXMLParser().parse(data),
    lambda data: RevisionResolver().resolve(data, RawDocument(())),
    lambda data: NumberingResolver().resolve(data, RawDocument(()), {}),
    run_pipeline,
    lambda data: validate_upload("test.docx", data),
]


@pytest.mark.parametrize("entry", ENTRY_POINTS)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_dtd_rejected_at_every_entry_point(entry, encoding, tmp_path):
    marker = tmp_path / "must-not-read.txt"
    marker.write_text("SECRET")
    xml = (f'<?xml version="1.0" encoding="{encoding}"?>'
           f'<!DOCTYPE w:document [<!ENTITY secret SYSTEM "{marker.as_uri()}">]>'
           f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&secret;</w:t></w:r></w:p></w:body></w:document>')
    with pytest.raises((PackageError, IngestError), match="DTD"):
        entry(package(xml.encode(encoding)))


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_expansion_limit_checked_before_parsing(entry):
    xml = b" " * (16 * 1024 * 1024 + 1)
    data = package(xml)
    assert len(data) < 100_000
    with pytest.raises((PackageError, IngestError)) as caught:
        entry(data)
    assert caught.value.http_status == 413


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_duplicate_parts_are_rejected(entry):
    with pytest.warns(UserWarning, match="Duplicate name"):
        data = package(extras=[("word/document.xml", XML)])
    with pytest.raises((PackageError, IngestError), match="повторяющиеся"):
        entry(data)


def test_crc_and_forged_size_are_rejected():
    original = package(compression=zipfile.ZIP_STORED)
    broken = bytearray(original)
    offset = original.index(b"<w:body>")
    broken[offset + 3] ^= 1
    with pytest.raises(PackageError):
        OOXMLParser().parse(bytes(broken))
    forged = bytearray(original)
    central = original.index(b"PK\x01\x02")
    struct.pack_into("<I", forged, central + 24, len(XML) - 1)
    with pytest.raises(PackageError):
        OOXMLParser().parse(bytes(forged))


def test_archive_entry_and_total_budgets(monkeypatch):
    monkeypatch.setattr("app.processing.docx_package.MAX_ZIP_ENTRIES", 3)
    with pytest.raises(PackageError, match="много частей"):
        DocxPackage(package(extras=[(f"p{i}", b"a") for i in range(3)]))
    monkeypatch.setattr("app.processing.docx_package.MAX_EXPANDED_BYTES", 1024)
    with pytest.raises(PackageError, match="общий лимит"):
        DocxPackage(package(extras=[("a", b"x" * 500), ("b", b"x" * 500)]))
    with pytest.raises(PackageError, match="метод сжатия"):
        DocxPackage(package(compression=zipfile.ZIP_BZIP2))


def test_node_depth_and_time_budgets_with_small_valid_control(monkeypatch):
    assert run_pipeline(docx(paragraph("1. Норма")))["clauses"]
    monkeypatch.setattr("app.processing.docx_package.MAX_XML_NODES", 20)
    with pytest.raises(PackageError, match="сложности XML"):
        run_pipeline(docx("<w:p/>" * 21))
    monkeypatch.setattr("app.processing.docx_package.MAX_XML_NODES", 250000)
    monkeypatch.setattr("app.processing.docx_package.MAX_XML_DEPTH", 6)
    with pytest.raises(PackageError, match="сложности XML"):
        run_pipeline(docx("<w:sdt>" * 8 + "</w:sdt>" * 8))
    clock = iter([0, 100])
    monkeypatch.setattr("app.processing.docx_package.monotonic", lambda: next(clock))
    with pytest.raises(PackageError, match="время"):
        run_pipeline(docx(paragraph("1. Норма")))


async def guard_request(chunks, extra_headers=(), method="POST", wrapped=None):
    messages = []
    chunks = iter(chunks)
    async def receive():
        return next(chunks)
    async def send(message):
        messages.append(message)
    async def endpoint(scope, receive, send):
        if wrapped:
            await wrapped(scope, receive, send)
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})
    guard = LocalRequestGuard(endpoint)
    await guard({"type": "http", "method": method, "path": "/api/documents",
                 "headers": [(b"host", b"localhost"), (b"content-type", b"multipart/form-data; boundary=b"), *extra_headers]}, receive, send)
    assert guard.active_uploads == 0
    return next(m["status"] for m in messages if m["type"] == "http.response.start")


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [[], [(b"content-length", b"4")]])
async def test_stream_limit_applies_before_app_even_without_correct_content_length(monkeypatch, headers):
    monkeypatch.setattr("app.api.request_guard.MAX_REQUEST_BYTES", 8)
    async def must_not_parse(*_):
        pytest.fail("Body parser must not be invoked")
    chunks = [{"type": "http.request", "body": b"12345", "more_body": True},
              {"type": "http.request", "body": b"6789", "more_body": False}]
    assert await guard_request(chunks, headers, wrapped=must_not_parse) == 413
    assert await guard_request([{"type": "http.request", "body": b"12345678"}]) == 204


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [[(b"origin", b"https://evil.example")], [(b"origin", b"null")], [(b"sec-fetch-site", b"cross-site")]])
async def test_foreign_origin_rejected_before_body(headers):
    assert await guard_request([], headers) == 403


@pytest.mark.asyncio
async def test_nonlocal_host_and_invalid_content_type_are_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://evil.example") as client:
        assert (await client.get("/health")).status_code == 400
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        assert (await client.post("/api/documents", data={"x": "y"})).status_code == 415
        assert (await client.get("/health", headers={"Origin": "disprot://app"})).status_code == 200
        assert (await client.get("/health", headers={"Origin": "http://localhost:3000"})).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,expected", [("extra_file", 400), ("text", 400), ("wrong_name", 400), ("header", 400), ("aggregate_headers", 413), ("truncated", 400)])
async def test_multipart_failures_close_files_and_have_no_side_effects(kind, expected, isolated_database, monkeypatch):
    import starlette.formparsers as parsers
    created = []
    real_spool = parsers.SpooledTemporaryFile
    def spool(*args, **kwargs):
        result = real_spool(*args, **kwargs)
        created.append(result)
        return result
    monkeypatch.setattr(parsers, "SpooledTemporaryFile", spool)
    def forbidden(*_):
        pytest.fail("Invalid upload reached a storage/background sink")
    monkeypatch.setattr("app.api.documents.FileStorage.put", forbidden)
    monkeypatch.setattr("app.api.documents.process_document", forbidden)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        if kind == "extra_file":
            response = await client.post("/api/documents", files=[("file", ("a.docx", package())), ("file", ("b.docx", package()))])
        elif kind == "text":
            response = await client.post("/api/documents", files={"file": ("a.docx", package())}, data={"x": "text"})
        elif kind == "wrong_name":
            response = await client.post("/api/documents", files={"other": ("a.docx", package())})
        else:
            body = b'--b\r\nContent-Disposition: form-data; name="file"; filename="a.docx"\r\n'
            if kind == "header":
                body += b'X-Long: ' + b'x' * 20000 + b'\r\n'
            if kind == "aggregate_headers":
                for i in range(5):
                    body += f"X-Long-{i}: ".encode() + b'x' * 3500 + b'\r\n'
            body += b'\r\n' + package()
            if kind in ("header", "aggregate_headers"):
                body += b'\r\n--b--\r\n'
            response = await client.post("/api/documents", content=body, headers={"Content-Type": "multipart/form-data; boundary=b"})
    assert response.status_code == expected, response.text
    assert all(file.closed for file in created)
    with isolated_database() as db:
        assert db.query(Document).count() == 0


@pytest.mark.asyncio
async def test_exact_file_limit_is_accepted_and_one_extra_byte_is_rejected(isolated_database, monkeypatch):
    saved, tasks = [], []
    monkeypatch.setattr("app.api.documents.FileStorage.put", lambda _, key, data: saved.append(len(data)))
    monkeypatch.setattr("app.api.documents.process_document", lambda document_id: tasks.append(document_id))
    base = package(extras=[("padding.bin", b"")], compression=zipfile.ZIP_STORED)
    padding = MAX_FILE_BYTES - len(base)
    data = package(extras=[("padding.bin", b"\0" * padding)], compression=zipfile.ZIP_STORED)
    assert len(data) == MAX_FILE_BYTES
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        good = await client.post("/api/documents", files={"file": ("limit.docx", data)})
        bad = await client.post("/api/documents", files={"file": ("over.docx", data + b"x")})
    assert good.status_code == 201, good.text
    assert bad.status_code == 413, bad.text
    assert saved == [MAX_FILE_BYTES] and len(tasks) == 1
    with isolated_database() as db:
        assert db.query(Document).count() == 1


def test_false_entry_count_cannot_bypass_preallocation_check(monkeypatch):
    data = bytearray(package(extras=[(f"p{i}", b"") for i in range(8)]))
    eocd = data.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", data, eocd + 8, 1, 1)
    monkeypatch.setattr("app.processing.docx_package.MAX_ZIP_ENTRIES", 4)
    def forbidden(*_):
        pytest.fail("ZipFile allocated entries before the directory limit")
    monkeypatch.setattr("app.processing.docx_package.zipfile.ZipFile", forbidden)
    with pytest.raises(PackageError, match="много частей"):
        DocxPackage(bytes(data))


def test_comments_count_towards_xml_complexity(monkeypatch):
    monkeypatch.setattr("app.processing.docx_package.MAX_XML_NODES", 20)
    with pytest.raises(PackageError, match="сложности XML"):
        run_pipeline(docx("<!-- comment -->" * 21))


def test_zip64_hidden_in_entry_comment_cannot_redirect_checked_directory(monkeypatch):
    original = package(extras=[(f"part{i}", b"") for i in range(8)])
    end = original.rfind(b"PK\x05\x06")
    _, _, _, _, count, size, offset, _ = struct.unpack_from("<4s4H2LH", original, end)
    names, extras, comments = struct.unpack_from("<3H", original, offset + 28)
    decoy = bytearray(original[offset:offset + 46 + names + extras + comments])
    struct.pack_into("<H", decoy, 32, 76)
    zip64_offset = end + len(decoy)
    hidden = struct.pack("<4sQ2H2I4Q", b"PK\x06\x06", 44, 45, 45, 0, 0,
                         count + 1, count + 1, size + len(decoy), offset)
    hidden += struct.pack("<4sIQI", b"PK\x06\x07", 0, zip64_offset, 1)
    small_end = struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 1, 1, len(decoy) + 76, end, 0)
    forged = original[:end] + decoy + hidden + small_end
    # The library actually selects the hidden directory, not the one-entry EOCD.
    with zipfile.ZipFile(BytesIO(forged)) as archive:
        assert len(archive.infolist()) == count + 1
    monkeypatch.setattr("app.processing.docx_package.MAX_ZIP_ENTRIES", 4)
    def forbidden(*_):
        pytest.fail("ZipFile allocated the unchecked ZIP64 directory")
    monkeypatch.setattr("app.processing.docx_package.zipfile.ZipFile", forbidden)
    with pytest.raises(PackageError, match="ZIP64"):
        DocxPackage(forged)


@pytest.mark.parametrize("entry", ENTRY_POINTS)
@pytest.mark.parametrize("tail_bytes,status", [(1, 400), (17 * 1024 * 1024, 413)])
def test_forged_size_and_crc_cannot_hide_actual_deflate_tail(entry, tail_bytes, status):
    forged = bytearray(package(XML + b" " * tail_bytes))
    central = forged.index(b"PK\x01\x02")
    for crc_offset, size_offset in ((14, 22), (central + 16, central + 24)):
        struct.pack_into("<I", forged, crc_offset, zlib.crc32(XML))
        struct.pack_into("<I", forged, size_offset, len(XML))
    with pytest.raises((PackageError, IngestError)) as caught:
        entry(bytes(forged))
    assert caught.value.http_status == status


@pytest.mark.parametrize("damage", ["truncated", "trailing", "concatenated"])
def test_deflate_must_reach_exactly_one_complete_stream(damage):
    original = package()
    central = original.index(b"PK\x01\x02")
    end = original.rfind(b"PK\x05\x06")
    names, extras = struct.unpack_from("<HH", original, 26)
    content = 30 + names + extras
    packed = original[content:central]
    packed = packed[:-1] if damage == "truncated" else packed + (b"junk" if damage == "trailing" else packed)
    header, directory, eocd = bytearray(original[:content]), bytearray(original[central:end]), bytearray(original[end:])
    struct.pack_into("<I", header, 18, len(packed))
    struct.pack_into("<I", directory, 20, len(packed))
    struct.pack_into("<I", eocd, 16, len(header) + len(packed))
    with pytest.raises(PackageError, match="поток"):
        DocxPackage(bytes(header + packed + directory + eocd))


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_valid_streaming_zip_data_descriptors_remain_supported(compression):
    class StreamingOutput(BytesIO):
        def seek(self, *_):
            raise OSError("Non-seekable output")
    output = StreamingOutput()
    with zipfile.ZipFile(output, "w", compression) as archive:
        archive.writestr("word/document.xml", XML)
    data = output.getvalue()
    assert struct.unpack_from("<H", data, 6)[0] & 8
    assert OOXMLParser().parse(data).blocks[0].text() == "1. Условие"


@pytest.mark.parametrize("stage", ["parser", "revisions", "numbering", "numbering_definitions", "styles"])
def test_shared_deadline_checked_during_cached_tree_processing(monkeypatch, stage):
    extras = []
    if stage == "numbering_definitions":
        definitions = "".join(f'<w:abstractNum w:abstractNumId="{i}"/>' for i in range(100))
        extras = [("word/numbering.xml", f'<w:numbering xmlns:w="{W}">{definitions}</w:numbering>'.encode())]
    elif stage == "styles":
        definitions = "".join(f'<w:style w:styleId="s{i}"/>' for i in range(100))
        extras = [("word/styles.xml", f'<w:styles xmlns:w="{W}">{definitions}</w:styles>'.encode())]
    xml = f'<w:document xmlns:w="{W}"><w:body>{paragraph("1. Условие") * 100}</w:body></w:document>'.encode()
    with DocxPackage(package(xml, extras)) as archive:
        raw = OOXMLParser().parse(archive)
        for name, _ in extras:
            archive.xml(name)
        ticks = 0
        def clock():
            nonlocal ticks
            ticks += 1
            return archive.started + (11 if ticks > 20 else 0)
        monkeypatch.setattr("app.processing.docx_package.monotonic", clock)
        with pytest.raises(PackageError, match="время") as caught:
            if stage == "parser":
                OOXMLParser().parse(archive)
            elif stage == "revisions":
                RevisionResolver().resolve(archive, raw)
            else:
                NumberingResolver().resolve(archive, raw if not extras else RawDocument(()), {})
        assert caught.value.http_status == 413


@pytest.mark.parametrize("owner,method", [
    ("ClauseSegmenter", "segment"), ("ChangedClauseDetector", "detect"), ("PartyExtractor", "extract"),
])
def test_pipeline_deadline_is_not_reset_between_stages(monkeypatch, owner, method):
    from app.services import ingestion
    clock = [0]
    monkeypatch.setattr("app.processing.docx_package.monotonic", lambda: clock[0])
    cls = getattr(ingestion, owner)
    original = getattr(cls, method)
    def delayed(*args, **kwargs):
        clock[0] = 11
        return original(*args, **kwargs)
    monkeypatch.setattr(cls, method, delayed)
    with pytest.raises(PackageError, match="время"):
        run_pipeline(docx(paragraph("1. Условие")))


def test_large_run_sequence_finishes_or_reports_deadline_without_hanging():
    # A subprocess gives the regression a hard guard if cooperative checks break.
    script = '''
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from app.processing.docx_package import PackageError
from app.processing.ooxml_parser import OOXMLParser
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
text = 'x' * 220
xml = ('<w:document xmlns:w="' + W + '"><w:body><w:p>' +
       ('<w:r><w:t>' + text + '</w:t></w:r>') * 50000 + '</w:p></w:body></w:document>').encode()
output = BytesIO()
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    archive.writestr('word/document.xml', xml)
try:
    raw = OOXMLParser().parse(output.getvalue())
    assert raw.blocks[0].text() == text * 50000
    print('complete')
except PackageError as error:
    assert error.http_status == 413 and 'время' in str(error)
    print('deadline')
'''
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() in ("complete", "deadline")
