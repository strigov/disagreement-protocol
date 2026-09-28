"""One resource boundary for every untrusted DOCX/ZIP/XML entry point."""
from __future__ import annotations

import zipfile
import struct
import zlib
from io import BytesIO
from time import monotonic

from lxml import etree

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_ZIP_ENTRIES = 2048
MAX_PART_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_DOCUMENT_XML_BYTES = 16 * 1024 * 1024
MAX_XML_BYTES = 26 * 1024 * 1024
MAX_XML_NODES = 250_000
MAX_XML_DEPTH = 128
MAX_PARSE_SECONDS = 10


class PackageError(ValueError):
    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status


def _check_extra(extra: bytes) -> None:
    cursor = 0
    while cursor < len(extra):
        if cursor + 4 > len(extra):
            raise PackageError("Повреждены дополнительные поля архива Word")
        kind, size = struct.unpack_from("<HH", extra, cursor)
        if kind == 1:
            raise PackageError("ZIP64 не поддерживается")
        cursor += 4 + size
    if cursor != len(extra):
        raise PackageError("Повреждены дополнительные поля архива Word")


def _check_directory(data: bytes) -> int:
    """Bound entries BEFORE ZipFile allocates a ZipInfo for every directory entry."""
    end = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
        raise PackageError("Файл повреждён или не является документом Word")
    _, disk, directory_disk, disk_count, count, size, offset, comment = struct.unpack_from("<4s4H2LH", data, end)
    if end + 22 + comment != len(data) or disk or directory_disk or disk_count != count:
        raise PackageError("Повреждённый или многотомный архив Word")
    # ZipFile consults this locator even when the ordinary EOCD has no ZIP64
    # sentinel values. It can be hidden inside the last entry's comment and
    # redirect ZipFile to a different, much larger directory than we checked.
    if end >= 20 and data[end - 20:end - 16] == b"PK\x06\x07":
        raise PackageError("ZIP64 не поддерживается")
    if count > MAX_ZIP_ENTRIES:
        raise PackageError("Слишком много частей в архиве Word", 413)
    if offset + size != end:
        raise PackageError("Некорректный каталог архива Word; ZIP64 не поддерживается")
    cursor, actual = offset, 0
    while cursor < end:
        if cursor + 46 > end or data[cursor:cursor + 4] != b"PK\x01\x02":
            raise PackageError("Повреждён каталог архива Word")
        name_len, extra_len, comment_len = struct.unpack_from("<3H", data, cursor + 28)
        if name_len > 1024 or extra_len > 4096 or comment_len > 4096:
            raise PackageError("Метаданные части архива Word превышают лимит", 413)
        extra_start = cursor + 46 + name_len
        if extra_start + extra_len + comment_len > end:
            raise PackageError("Повреждён каталог архива Word")
        _check_extra(data[extra_start:extra_start + extra_len])
        cursor += 46 + name_len + extra_len + comment_len
        actual += 1
        if actual > MAX_ZIP_ENTRIES:
            raise PackageError("Слишком много частей в архиве Word", 413)
    if cursor != end or actual != count:
        raise PackageError("Количество частей архива не совпадает с каталогом")
    return offset


class _LimitedTreeBuilder(etree.TreeBuilder):
    def __init__(self, package):
        super().__init__(insert_comments=True, insert_pis=True)
        self.package = package
        self.depth = 0
        self.failure: PackageError | None = None

    def _reject(self, message, status=400):
        self.failure = PackageError(message, status)
        raise self.failure

    def start(self, tag, attrs, nsmap=None):
        self.depth += 1
        self.package.nodes += 1 + len(attrs) + len(nsmap or {})
        if self.depth > MAX_XML_DEPTH or self.package.nodes > MAX_XML_NODES:
            self._reject("Документ превышает лимит сложности XML", 413)
        return super().start(tag, attrs, nsmap)

    def _count_misc_node(self):
        self.package.nodes += 1
        if self.package.nodes > MAX_XML_NODES:
            self._reject("Документ превышает лимит сложности XML", 413)

    def comment(self, text):
        self._count_misc_node()
        return super().comment(text)

    def pi(self, target, data):
        self._count_misc_node()
        return super().pi(target, data)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)

    def doctype(self, name, pubid, system):
        # Parser callback works for UTF-8/UTF-16 and fires before any expansion.
        self._reject("DTD и объявления сущностей в документе Word запрещены")


class DocxPackage:
    def __init__(self, data: bytes):
        if len(data) > MAX_FILE_BYTES:
            raise PackageError("Размер файла превышает 25 MB", 413)
        self.started = monotonic()
        self.directory_offset = _check_directory(data)
        self.data = data
        self.nodes = 0
        self.xml_bytes = 0
        self.roots = {}
        try:
            self.archive = zipfile.ZipFile(BytesIO(data))
        except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError) as exc:
            raise PackageError("Файл повреждён или не является документом Word") from exc
        try:
            entries = self.archive.infolist()
            if len(entries) > MAX_ZIP_ENTRIES:
                raise PackageError("Слишком много частей в архиве Word", 413)
            self.entries = {}
            total = 0
            for info in entries:
                self.check_budget()
                if info.filename in self.entries:
                    raise PackageError("Архив Word содержит повторяющиеся имена частей")
                self.entries[info.filename] = info
                if info.flag_bits & 0x61 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise PackageError("Шифрование или метод сжатия архива Word не поддерживается", 415)
                if info.file_size > MAX_PART_BYTES:
                    raise PackageError("Часть архива Word превышает лимит распакованного размера", 413)
                total += info.file_size
            if total > MAX_EXPANDED_BYTES:
                raise PackageError("Архив Word превышает общий лимит распакованного размера", 413)
            offsets = sorted(info.header_offset for info in entries)
            if len(set(offsets)) != len(offsets):
                raise PackageError("Части архива Word перекрываются")
            bounds = dict(zip(offsets, offsets[1:] + [self.directory_offset]))
            self.parts = {
                info.filename: self._part_bounds(info, bounds[info.header_offset])
                for info in entries
            }
            if "word/document.xml" not in self.entries:
                raise PackageError("В архиве отсутствует word/document.xml — это не Word-документ")
            if any(name.lower().endswith("vbaproject.bin") for name in self.entries):
                raise PackageError("Документ содержит макросы (vbaProject.bin) — не поддерживается", 415)
            if self.entries["word/document.xml"].file_size > MAX_DOCUMENT_XML_BYTES:
                raise PackageError("Основной XML документа превышает лимит 16 MiB", 413)
            self.xml("word/document.xml")
        except Exception:
            self.archive.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.archive.close()

    def check_budget(self) -> None:
        if monotonic() - self.started > MAX_PARSE_SECONDS:
            raise PackageError("Превышено время разбора документа Word", 413)

    def checked(self, items):
        """Use the same deadline while processing already parsed XML and models."""
        for item in items:
            self.check_budget()
            yield item
        self.check_budget()

    def _part_bounds(self, info, bound: int) -> tuple[int, int]:
        self.check_budget()
        start = info.header_offset
        if start < 0 or start + 30 > bound or bound > self.directory_offset:
            raise PackageError("Части архива Word перекрываются")
        signature, _, flags, method, _, _, crc, packed, unpacked, names, extras = struct.unpack_from(
            "<4s5H3I2H", self.data, start,
        )
        if signature != b"PK\x03\x04" or method != info.compress_type or flags != info.flag_bits:
            raise PackageError("Заголовок части архива Word не совпадает с каталогом")
        if names > 1024 or extras > 4096:
            raise PackageError("Метаданные части архива Word превышают лимит", 413)
        if packed == 0xFFFFFFFF or unpacked == 0xFFFFFFFF:
            raise PackageError("ZIP64 не поддерживается")
        content_start = start + 30 + names + extras
        content_end = content_start + info.compress_size
        if content_end > bound:
            raise PackageError("Части архива Word перекрываются")
        raw_name = self.data[start + 30:start + 30 + names]
        try:
            name = raw_name.decode("utf-8" if flags & 0x800 else "cp437")
        except UnicodeError as exc:
            raise PackageError("Некорректное имя части архива Word") from exc
        if "\0" in name or name != info.orig_filename:
            raise PackageError("Имя части архива Word не совпадает с каталогом")
        _check_extra(self.data[start + 30 + names:content_start])
        expected = (info.CRC, info.compress_size, info.file_size)
        actual = (crc, packed, unpacked)
        if flags & 8:  # Streaming ZIP writers put final values in a data descriptor.
            if any(value not in (0, target) for value, target in zip(actual, expected)):
                raise PackageError("Размер или CRC части архива Word не совпадает с каталогом")
            descriptor_starts = [content_end]
            if self.data[content_end:content_end + 4] == b"PK\x07\x08":
                descriptor_starts.append(content_end + 4)
            if not any(pos + 12 <= bound and struct.unpack_from("<3I", self.data, pos) == expected
                       for pos in descriptor_starts):
                raise PackageError("Повреждён дескриптор части архива Word")
        elif actual != expected:
            raise PackageError("Размер или CRC части архива Word не совпадает с каталогом")
        return content_start, content_end

    def _read_part(self, info, limit: int):
        """Read the actual stream end; ZipExtFile truncates at claimed file_size."""
        cursor, end = self.parts[info.filename]
        consumed, crc = 0, 0
        decoder = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
        pending = b""
        while True:
            self.check_budget()
            if not pending and cursor < end:
                pending = self.data[cursor:min(cursor + 64 * 1024, end)]
                cursor += len(pending)
            if decoder is None:
                chunk, pending = pending, b""
            else:
                chunk = decoder.decompress(pending, min(64 * 1024, limit - consumed + 1))
                pending = decoder.unconsumed_tail
            consumed += len(chunk)
            if consumed > limit:
                raise PackageError("Превышен лимит распакованного XML", 413)
            crc = zlib.crc32(chunk, crc)
            if chunk:
                yield chunk
            if decoder is None:
                if cursor == end:
                    break
            elif decoder.eof:
                if decoder.unused_data or cursor != end:
                    raise PackageError("Лишние данные после сжатого потока части Word")
                break
            elif not chunk and not pending and cursor == end:
                raise PackageError("Незавершённый сжатый поток части Word")
        if consumed != info.file_size or crc != info.CRC:
            raise PackageError("Фактический размер или CRC части Word не совпадает с заявленным")

    def xml(self, name: str, limit: int = MAX_DOCUMENT_XML_BYTES):
        self.check_budget()
        if name in self.roots:
            return self.roots[name]
        info = self.entries.get(name)
        if info is None:
            return None
        if info.file_size > limit:
            raise PackageError(f"Часть {name} превышает лимит размера XML", 413)
        target = _LimitedTreeBuilder(self)
        parser = etree.XMLParser(
            target=target, resolve_entities=False, load_dtd=False,
            no_network=True, recover=False, huge_tree=False,
        )
        try:
            for chunk in self._read_part(info, limit):
                self.xml_bytes += len(chunk)
                if self.xml_bytes > MAX_XML_BYTES:
                    raise PackageError("Превышен лимит распакованного XML", 413)
                parser.feed(chunk)
            root = parser.close()
            self.check_budget()
        except PackageError:
            raise
        except (zipfile.BadZipFile, zlib.error, etree.XMLSyntaxError, OSError, EOFError, RuntimeError) as exc:
            if target.failure is not None:
                # TreeBuilder.close() can mask the callback failure with
                # "missing end tags". Keep the actual policy reason/status.
                raise target.failure from exc
            raise PackageError(f"Повреждена часть документа Word: {name}") from exc
        self.roots[name] = root
        return root
