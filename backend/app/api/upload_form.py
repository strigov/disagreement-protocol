"""Multipart limits applied during parsing, with cleanup on every failure path."""
from starlette.formparsers import MultiPartException, MultiPartParser
from python_multipart.multipart import parse_options_header


class UploadLimitError(MultiPartException):
    pass


class SingleFileParser(MultiPartParser):
    def __init__(self, headers, stream, max_bytes):
        super().__init__(headers, stream, max_files=1, max_fields=0, max_part_size=1024)
        self.max_bytes = max_bytes
        self.header_bytes = 0
        self.file_bytes = 0
        self.finished = False

    def on_part_begin(self):
        super().on_part_begin()
        self.header_bytes = 0

    def _count_header(self, size):
        self.header_bytes += size
        if self.header_bytes > 16 * 1024:
            raise UploadLimitError("Заголовки части multipart превышают 16 KiB")

    def on_header_field(self, data, start, end):
        self._count_header(end - start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data, start, end):
        self._count_header(end - start)
        super().on_header_value(data, start, end)

    def on_headers_finished(self):
        super().on_headers_finished()
        if self._current_part.field_name != "file" or self._current_part.file is None:
            raise MultiPartException("Выберите один файл договора.")

    def on_part_data(self, data, start, end):
        self.file_bytes += end - start
        if self.file_bytes > self.max_bytes:
            raise UploadLimitError("Размер файла превышает 25 МБ")
        super().on_part_data(data, start, end)

    def on_end(self):
        self.finished = True

    async def parse(self):
        _, options = parse_options_header(self.headers.get("content-type", ""))
        boundary = options.get(b"boundary", b"")
        if not boundary or len(boundary) > 200:
            raise MultiPartException("Некорректная граница multipart")
        try:
            form = await super().parse()
            if not self.finished:
                raise MultiPartException("Загрузка multipart прервана до завершающей границы")
            return form
        except BaseException:
            # Includes unclosed parts which have not yet entered FormData.items.
            for file in self._files_to_close_on_error:
                file.close()
            raise
        finally:
            close_stream = getattr(self.stream, "aclose", None)
            if close_stream is not None:
                await close_stream()
