"""Windows desktop entry point; all runtime dependencies ship in the bundle."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

TITLE = "Протокол разногласий"
FRONTEND_PORT = 17341
BACKEND_PORT = 17342
URL = f"http://127.0.0.1:{FRONTEND_PORT}"
MUTEX_NAME = r"Local\DisagreementProtocol.Desktop"
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


class ChildJob:
    """Ensure Node exits even if the launcher is terminated unexpectedly."""

    def __init__(self):
        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64),
                ("Flags", wintypes.DWORD), ("MinWorkingSet", ctypes.c_size_t),
                ("MaxWorkingSet", ctypes.c_size_t), ("ActiveProcesses", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD),
                ("Scheduling", wintypes.DWORD),
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("Basic", BasicLimits), ("IoCounters", ctypes.c_uint64 * 6),
                ("ProcessMemory", ctypes.c_size_t), ("JobMemory", ctypes.c_size_t),
                ("PeakProcessMemory", ctypes.c_size_t), ("PeakJobMemory", ctypes.c_size_t),
            ]

        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self.handle = kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process):
        if not kernel32.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None


def reserve_port(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as exc:
        sock.close()
        raise RuntimeError(
            f"Порт {port} занят другим приложением. Закройте его и запустите программу снова."
        ) from exc
    return sock


class Runtime:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.failed = False
        self.thread = threading.Thread(target=self.run, name="desktop-runtime")

    def run(self):
        node = server = backend = job = backend_socket = frontend_socket = None
        try:
            bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
            backend_socket = reserve_port(BACKEND_PORT)
            frontend_socket = reserve_port(FRONTEND_PORT)
            os.environ["DISPROT_UI_PORT"] = str(FRONTEND_PORT)
            os.environ["DATABASE_URL"] = "sqlite:///" + (self.data_dir / "disprot.db").as_posix()
            os.environ["STORAGE_DIR"] = str(self.data_dir / "files")
            # Ignore a .env in whichever directory the executable was opened from.
            from app.config import get_settings
            get_settings.cache_clear()
            from app import config
            config.Settings.model_config["env_file"] = None
            from app.main import app
            import uvicorn

            server = uvicorn.Server(uvicorn.Config(
                app, host="127.0.0.1", port=BACKEND_PORT, loop="asyncio", http="h11", ws="none",
                lifespan="on", log_config=None, access_log=False, timeout_graceful_shutdown=30,
            ))
            backend = threading.Thread(target=server.run, kwargs={"sockets": [backend_socket]}, name="backend")
            backend.start()
            deadline = time.monotonic() + 90
            while not server.started:
                if self.stop.wait(0.1):
                    return
                if not backend.is_alive():
                    raise RuntimeError("Не удалось запустить обработку документов. Подробности в журнале.")
                if time.monotonic() > deadline:
                    raise RuntimeError("Истекло время запуска обработки документов.")

            job = ChildJob()
            env = os.environ.copy()
            for name in ("NODE_OPTIONS", "NODE_PATH", "NODE_EXTRA_CA_CERTS", "__NEXT_PRIVATE_STANDALONE_CONFIG"):
                env.pop(name, None)
            env.update(HOSTNAME="127.0.0.1", PORT=str(FRONTEND_PORT), NODE_ENV="production", NEXT_TELEMETRY_DISABLED="1")
            frontend_socket.close()
            frontend_socket = None
            with (self.data_dir / "logs" / "frontend.log").open("w", encoding="utf-8") as node_log:
                node = subprocess.Popen(
                    [str(bundle / "node.exe"), str(bundle / "frontend" / "server.js")],
                    cwd=bundle / "frontend", env=env, stdin=subprocess.DEVNULL,
                    stdout=node_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                )
                job.assign(node)
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                while not self.stop.is_set():
                    if node.poll() is not None:
                        raise RuntimeError("Не удалось запустить интерфейс. Подробности в logs/frontend.log.")
                    try:
                        with opener.open(URL, timeout=1) as response:
                            if response.status == 200:
                                break
                    except (OSError, urllib.error.URLError):
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError("Истекло время запуска интерфейса.")
                    self.stop.wait(0.2)
                if self.stop.is_set():
                    return
                self.events.put(("ready", None))
                while not self.stop.wait(0.5):
                    if node.poll() is not None or not backend.is_alive():
                        raise RuntimeError("Приложение неожиданно остановилось. Подробности в журнале.")
        except Exception as exc:
            self.failed = True
            logging.exception("Desktop runtime failed")
            self.events.put(("error", str(exc)))
        finally:
            if node is not None and node.poll() is None:
                node.terminate()
                node.wait(timeout=10)
            if job is not None:
                job.close()
            if server is not None:
                server.should_exit = True
            if backend is not None:
                backend.join()
            for sock in (backend_socket, frontend_socket):
                if sock is not None:
                    sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args()
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        if not args.no_browser:
            webbrowser.open(URL)
        kernel32.CloseHandle(mutex)
        return 0
    data_dir = (args.data_dir or Path(os.environ["LOCALAPPDATA"]) / "DisagreementProtocol").resolve()
    try:
        (data_dir / "logs").mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(data_dir / "logs" / "desktop.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
        runtime = Runtime(data_dir)
        if args.headless:
            runtime.thread.start()
            try:
                while runtime.thread.is_alive():
                    if args.stop_file and args.stop_file.exists():
                        runtime.stop.set()
                    runtime.thread.join(timeout=0.2)
            finally:
                runtime.stop.set()
                runtime.thread.join()
        else:
            import tkinter as tk
            from tkinter import ttk, messagebox

            root = tk.Tk()
            root.title(TITLE)
            root.geometry("540x255")
            root.resizable(False, False)
            frame = ttk.Frame(root, padding=24)
            frame.pack(fill="both", expand=True)
            ttk.Label(frame, text=TITLE, font=("Segoe UI", 17, "bold")).pack(anchor="w")
            status = tk.StringVar(value="Запускаем приложение…")
            ttk.Label(frame, textvariable=status, wraplength=485).pack(anchor="w", pady=(16, 12))
            open_button = ttk.Button(frame, text="Открыть в браузере", state="disabled", command=lambda: webbrowser.open(URL))
            open_button.pack(anchor="w")
            ttk.Button(frame, text="Открыть папку данных", command=lambda: os.startfile(data_dir)).pack(anchor="w", pady=8)
            closing = False

            def close():
                nonlocal closing
                closing = True
                runtime.stop.set()
                open_button.configure(state="disabled")
                status.set("Завершаем обработку и сохраняем данные…")

            def tick():
                if args.stop_file and args.stop_file.exists():
                    close()
                while not runtime.events.empty():
                    kind, detail = runtime.events.get_nowait()
                    if kind == "ready" and not closing:
                        status.set("Приложение работает. Закройте это окно, чтобы остановить его.")
                        open_button.configure(state="normal")
                        if not args.no_browser:
                            webbrowser.open(URL)
                    elif kind == "error":
                        status.set(detail)
                        open_button.configure(state="disabled")
                        messagebox.showerror(TITLE, f"{detail}\n\nЖурналы: {data_dir / 'logs'}")
                if closing and not runtime.thread.is_alive():
                    root.destroy()
                else:
                    root.after(200, tick)

            root.protocol("WM_DELETE_WINDOW", close)
            runtime.thread.start()
            root.after(200, tick)
            try:
                root.mainloop()
            finally:
                runtime.stop.set()
                runtime.thread.join()
        return 1 if runtime.failed else 0
    finally:
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    sys.exit(main())
