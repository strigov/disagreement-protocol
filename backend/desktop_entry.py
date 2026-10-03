"""Frozen engine entrypoint. The desktop launcher owns its stdin and lifetime."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import sys
import threading


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    token = os.environ.pop("DISPROT_DESKTOP_TOKEN", "")
    if not re.fullmatch(r"[a-f0-9]{64}", token):
        parser.error("The desktop launcher must supply a session token")
    data_dir = Path(args.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    # Do not inherit developer .env files or a database from the install directory.
    os.environ["DISPROT_DATA_DIR"] = str(data_dir)
    from app.config import get_settings
    get_settings.cache_clear()

    import uvicorn
    from app.main import create_app

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        server = uvicorn.Server(uvicorn.Config(
            create_app(desktop_token=token), host="127.0.0.1",
            loop="asyncio", http="h11", ws="none", lifespan="on",
            access_log=False, timeout_graceful_shutdown=5,
        ))

        def watch_parent() -> None:
            # Closing the app or losing the parent closes the pipe on both OSes.
            sys.stdin.buffer.readline()
            server.should_exit = True

        threading.Thread(target=watch_parent, daemon=True).start()
        print("DISPROT_READY=" + json.dumps({"port": sock.getsockname()[1]}), flush=True)
        server.run(sockets=[sock])


if __name__ == "__main__":
    main()
