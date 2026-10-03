"""Exercise an actual frozen EXE with a clean PATH and isolated persistent data."""
import argparse
from contextlib import contextmanager
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:17341"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path, method="GET", data=None, headers=None):
    headers = {"Origin": BASE, **(headers or {})}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    with HTTP.open(urllib.request.Request(BASE + path, data=data, headers=headers, method=method), timeout=30) as response:
        raw = response.read()
        return json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw


def check_ports_free():
    for port in (17341, 17342):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(("127.0.0.1", port))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--gui", action="store_true", help="Also exercise the Tk desktop window")
    args = parser.parse_args()
    check_ports_free()
    with tempfile.TemporaryDirectory(prefix="disprot smoke ") as temp:
        work = Path(temp)
        executable = args.executable.resolve()
        if "Portable" in executable.name:
            executable = Path(shutil.copy2(executable, work / executable.name))
        data_dir = work / "Данные пользователя"
        stop = work / "stop"
        env = os.environ.copy()
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "NODE_PATH", "NODE_OPTIONS"):
            env.pop(key, None)
        command = [str(executable), "--no-browser", "--data-dir", str(data_dir), "--stop-file", str(stop)]
        if not args.gui:
            command.append("--headless")

        @contextmanager
        def running():
            stop.unlink(missing_ok=True)
            process = subprocess.Popen(command, cwd=work, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline = time.monotonic() + 120
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f"EXE exited early ({process.returncode})")
                    try:
                        page = request("/")
                        assert "Протокол" in page.decode()
                        break
                    except (OSError, urllib.error.URLError):
                        if time.monotonic() > deadline:
                            raise RuntimeError("EXE did not become ready")
                        time.sleep(0.25)
                yield page
            except Exception:
                for log in (data_dir / "logs").glob("*.log"):
                    print(log.name, log.read_text(encoding="utf-8", errors="replace"), flush=True)
                raise
            finally:
                stop.touch()
                try:
                    code = process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise RuntimeError("EXE did not stop cleanly")
                assert code == 0, f"EXE exit code: {code}"
                check_ports_free()

        with running() as page:
            print("PASS: standalone runtime starts without Python or Node on PATH", flush=True)
            assets = set(re.findall(r'(?:src|href)="([^" ]+\.(?:js|css))"', page.decode()))
            assert assets
            for asset in assets:
                assert request(asset)
            print(f"PASS: home page and {len(assets)} JavaScript/CSS assets", flush=True)
            for headers in ({"Origin": "https://untrusted.example"}, {"Host": "untrusted.example"}):
                try:
                    request("/api/protocols", headers=headers)
                    raise AssertionError("Foreign request was accepted")
                except urllib.error.HTTPError as exc:
                    assert exc.code in (400, 403)
            with HTTP.open(urllib.request.Request("http://127.0.0.1:17342/health", headers={"Origin": BASE})) as response:
                assert json.loads(response.read()) == {"status": "ok"}
            try:
                HTTP.open(urllib.request.Request("http://127.0.0.1:17342/health", headers={"Origin": "http://127.0.0.1:3000"}))
                raise AssertionError("Desktop backend accepted the development UI origin")
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
            duplicate = subprocess.run(command, cwd=work, env=env, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            assert duplicate.returncode == 0
            print("PASS: foreign requests rejected; second launch keeps one instance", flush=True)
            sample = (ROOT / "samples" / "01_simple_manual_numbering.docx").read_bytes()
            boundary = "disprot-smoke-test-boundary"
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="contract.docx"\r\n'
                    'Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode()
            body += sample + f"\r\n--{boundary}--\r\n".encode()
            created = request("/api/documents", "POST", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
            doc_id = created["id"]
            for _ in range(120):
                analysis = request(f"/api/documents/{doc_id}/analysis")
                if analysis["status"] == "parsed":
                    break
                assert analysis["status"] != "failed", analysis
                time.sleep(0.25)
            assert analysis["status"] == "parsed", analysis
            parties = analysis["parties"]
            if len(parties) != 2:
                analysis = request(f"/api/documents/{doc_id}/parties", "PATCH", {"parties": [
                    {"name": "Компания А", "role": "Поставщик"}, {"name": "Компания Б", "role": "Покупатель"},
                ]})
                parties = analysis["parties"]
            request(f"/api/documents/{doc_id}/parties", "PATCH", {"parties": parties, "drafting_party_id": parties[0]["id"]})
            protocol = request(f"/api/documents/{doc_id}/protocol", "POST")
            assert protocol["rows"], protocol
            row = protocol["rows"][0]
            edit = "Проверка автономной Windows-сборки: согласованная редакция."
            request(f'/api/protocols/{protocol["id"]}/rows/{row["id"]}', "PATCH", {"agreed_text": edit})
            exported = request(f"/api/documents/{doc_id}/protocol/export", "POST", {"filename": "Тест"})
            with zipfile.ZipFile(BytesIO(exported)) as docx:
                assert edit in docx.read("word/document.xml").decode()
            for route in ("analysis", "parties", "protocol", "export"):
                assert request(f"/documents/{doc_id}/{route}")
            print(f'PASS: upload, analysis, parties, {len(protocol["rows"])} protocol rows, edit and DOCX export', flush=True)
        with running():
            restored = request(f'/api/protocols/{protocol["id"]}/rows')
            assert restored["rows"][0]["agreed_text"] == edit
            print("PASS: database and edits survive restart; ports released on close", flush=True)
        # A busy port must produce a clear error without disturbing its owner.
        with socket.socket() as occupied:
            occupied.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            occupied.bind(("127.0.0.1", 17341))
            occupied.listen()
            stop.unlink(missing_ok=True)
            conflict_command = [str(executable), "--headless", "--no-browser", "--data-dir", str(data_dir)]
            result = subprocess.run(conflict_command, cwd=work, env=env, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
            assert result.returncode == 1
            assert "Порт 17341 занят" in (data_dir / "logs" / "desktop.log").read_text(encoding="utf-8")
            print("PASS: occupied port handled without killing another application", flush=True)
        check_ports_free()
    print("ALL WINDOWS PACKAGE SMOKE CHECKS PASSED", flush=True)


if __name__ == "__main__":
    main()
