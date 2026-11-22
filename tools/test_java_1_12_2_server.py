"""Smoke-test the protocol client against a genuine Minecraft 1.12.2 server."""
from __future__ import annotations

import time

from engine.network.status import query_server
from engine.network.login import login_offline


HOST = "127.0.0.1"
PORT = 25565
USERNAME = "MPEInteropTest"


def main() -> None:
    last_error = None
    status = None
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            status = query_server(HOST, PORT, timeout=3)
            break
        except OSError as exc:
            last_error = exc
            time.sleep(2)
    if status is None:
        raise SystemExit(f"server did not become ready: {last_error}")
    if status.protocol != 340:
        raise SystemExit(f"wrong server protocol: {status.protocol}")
    if status.version_name != "1.12.2":
        raise SystemExit(f"wrong server version: {status.version_name}")

    connection, identity = login_offline(HOST, PORT, USERNAME, timeout=10)
    try:
        if identity.username != USERNAME:
            raise SystemExit("server returned unexpected player name")
        print(f"STATUS_OK version={status.version_name} protocol={status.protocol}")
        print(f"LOGIN_OK username={identity.username} uuid={identity.player_uuid}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
