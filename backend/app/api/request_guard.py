"""Reject oversized or cross-site local requests before FastAPI parses a body."""
import asyncio
import os
from tempfile import SpooledTemporaryFile
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

from app.processing.docx_package import MAX_FILE_BYTES

MAX_REQUEST_BYTES = MAX_FILE_BYTES + 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}
UI_PORT = int(os.environ.get("DISPROT_UI_PORT", "3000"))
if not 1 <= UI_PORT <= 65535:
    raise ValueError("DISPROT_UI_PORT must be a valid TCP port")
ALLOWED_ORIGINS = {f"http://localhost:{UI_PORT}", f"http://127.0.0.1:{UI_PORT}"}


class LocalRequestGuard:
    def __init__(self, app):
        self.app = app
        self.active_uploads = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

        raw_headers = scope.get("headers", [])
        headers = {key.lower(): value for key, value in raw_headers}
        if sum(len(k) + len(v) for k, v in raw_headers) > 16 * 1024:
            return await reject(431, "Слишком большие заголовки запроса")
        hosts = [v for k, v in raw_headers if k.lower() == b"host"]
        try:
            host = urlsplit("http://" + hosts[0].decode("ascii")).hostname if len(hosts) == 1 else None
        except (ValueError, UnicodeDecodeError):
            host = None
        if host not in ALLOWED_HOSTS:
            return await reject(400, "Приложение доступно только по локальному адресу")
        origin = headers.get(b"origin")
        if origin is not None and origin.decode("latin-1") not in ALLOWED_ORIGINS:
            return await reject(403, "Запрос с постороннего сайта запрещён")
        if headers.get(b"sec-fetch-site") == b"cross-site":
            return await reject(403, "Запрос с постороннего сайта запрещён")

        if scope["method"] in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        upload = scope["method"] == "POST" and scope["path"].rstrip("/") == "/api/documents"
        if headers.get(b"content-encoding", b"identity").lower() != b"identity":
            return await reject(415, "Сжатие HTTP-тела не поддерживается")
        if upload and headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower() != b"multipart/form-data":
            return await reject(415, "Загрузка требует multipart/form-data с одним файлом")
        limit = MAX_REQUEST_BYTES if upload else MAX_JSON_BYTES
        lengths = [v for k, v in raw_headers if k.lower() == b"content-length"]
        if len(lengths) > 1 or (lengths and (not lengths[0].isdigit())):
            return await reject(400, "Некорректный Content-Length")
        if lengths and int(lengths[0]) > limit:
            return await reject(413, "Размер запроса превышает допустимый лимит")
        if upload and self.active_uploads >= 2:
            return await reject(503, "Уже обрабатываются две загрузки. Повторите после их завершения.")
        if upload:
            self.active_uploads += 1
        try:
            # Disk spool bounds memory, and parsing starts only after the full
            # request (including ignored parts/epilogue) has passed the byte cap.
            with SpooledTemporaryFile(max_size=1024 * 1024) as body:
                size = 0
                try:
                    async with asyncio.timeout(30):
                        while True:
                            message = await receive()
                            if message["type"] == "http.disconnect":
                                return
                            chunk = message.get("body", b"")
                            size += len(chunk)
                            if size > limit:
                                return await reject(413, "Размер запроса превышает допустимый лимит")
                            body.write(chunk)
                            if not message.get("more_body", False):
                                break
                except TimeoutError:
                    return await reject(408, "Истекло время загрузки запроса")
                if lengths and size != int(lengths[0]):
                    return await reject(400, "Размер запроса не совпадает с Content-Length")
                body.seek(0)

                async def replay():
                    data = body.read(64 * 1024)
                    return {"type": "http.request", "body": data, "more_body": body.tell() < size}

                await self.app(scope, replay, send)
        finally:
            if upload:
                self.active_uploads -= 1
