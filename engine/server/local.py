"""Small LAN server for Python Edition clients (not Java protocol compatible).

The transport is newline-delimited UTF-8 JSON. The first message must identify
itself as MinecraftPythonEdition; Java Edition clients are intentionally rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import socketserver
import threading
import time
import uuid

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 64 * 1024


class ServerError(RuntimeError):
    """Local multiplayer server lifecycle or protocol error."""


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 25575
    max_players: int = 8
    motd: str = "Minecraft Python Edition Server"

    def __post_init__(self):
        if not isinstance(self.host, str) or not self.host:
            raise ValueError("host must be a non-empty string")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 0 <= self.port <= 65535:
            raise ValueError("port must be from 0 to 65535")
        if isinstance(self.max_players, bool) or not isinstance(self.max_players, int) or not 1 <= self.max_players <= 255:
            raise ValueError("max_players must be from 1 to 255")
        if not isinstance(self.motd, str) or len(self.motd) > 256:
            raise ValueError("motd must be a string of at most 256 characters")


class _ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False


class PythonEditionServer:
    """Threaded Python-only LAN host with admission, chat, and player-state relay.

    This is a deliberately separate protocol from Java protocol 340. A client
    must send {type: hello, edition: MinecraftPythonEdition, protocol: 1,
    username: ...} before it is admitted.
    """

    def __init__(self, config: ServerConfig | None = None, *, on_event=None):
        self.config = config or ServerConfig()
        if on_event is not None and not callable(on_event):
            raise TypeError("on_event must be callable")
        self.on_event = on_event
        self._lock = threading.RLock()
        self._clients: dict[socket.socket, dict] = {}
        self._thread = None
        self._server = None
        self._stopping = threading.Event()

    @property
    def running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    @property
    def address(self) -> tuple[str, int] | None:
        if self._server is None:
            return None
        return self._server.server_address[:2]

    @property
    def player_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _emit(self, event: str, **data):
        if self.on_event is not None:
            self.on_event(event, data)

    @staticmethod
    def _encode(message: dict) -> bytes:
        raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ServerError("outgoing message exceeds size limit")
        return raw

    def _send(self, sock: socket.socket, message: dict) -> bool:
        try:
            sock.sendall(self._encode(message))
            return True
        except (OSError, ServerError):
            return False

    def broadcast(self, message: dict, *, exclude=None) -> int:
        payload = self._encode(message)
        with self._lock:
            clients = tuple(sock for sock in self._clients if sock is not exclude)
        sent = 0
        for sock in clients:
            try:
                sock.sendall(payload)
                sent += 1
            except OSError:
                self._drop(sock)
        return sent

    def _drop(self, sock: socket.socket):
        with self._lock:
            info = self._clients.pop(sock, None)
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass
        if info is not None:
            self.broadcast({"type": "player_left", "username": info["username"]})
            self._emit("player_left", username=info["username"])

    def start(self) -> tuple[str, int]:
        if self._server is not None:
            raise ServerError("server has already been started")
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                sock = self.request
                sock.settimeout(10.0)
                try:
                    first = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
                    if not first or len(first) > MAX_MESSAGE_BYTES:
                        return
                    hello = json.loads(first.decode("utf-8"))
                    if (not isinstance(hello, dict) or hello.get("type") != "hello"
                            or hello.get("edition") != "MinecraftPythonEdition"
                            or hello.get("protocol") != PROTOCOL_VERSION):
                        owner._send(sock, {"type": "disconnect", "reason": "Python Edition clients only"})
                        return
                    username = hello.get("username")
                    if not isinstance(username, str) or not 1 <= len(username) <= 16:
                        owner._send(sock, {"type": "disconnect", "reason": "Invalid username"})
                        return
                    with owner._lock:
                        if len(owner._clients) >= owner.config.max_players:
                            owner._send(sock, {"type": "disconnect", "reason": "Server is full"})
                            return
                        if any(p["username"].casefold() == username.casefold()
                               for p in owner._clients.values()):
                            owner._send(sock, {"type": "disconnect", "reason": "Username is already online"})
                            return
                        player_id = str(uuid.uuid4())
                        owner._clients[sock] = {"username": username, "uuid": player_id,
                                                "joined_at": time.time()}
                    self.wfile.write(owner._encode({
                        "type": "welcome", "protocol": PROTOCOL_VERSION,
                        "uuid": player_id, "username": username,
                        "motd": owner.config.motd,
                        "online": owner.player_count,
                        "max_players": owner.config.max_players,
                    }))
                    owner.broadcast({"type": "player_joined", "username": username}, exclude=sock)
                    owner._emit("player_joined", username=username, uuid=player_id)
                    sock.settimeout(None)
                    while not owner._stopping.is_set():
                        line = self.rfile.readline(MAX_MESSAGE_BYTES + 1)
                        if not line:
                            break
                        if len(line) > MAX_MESSAGE_BYTES:
                            owner._send(sock, {"type": "disconnect", "reason": "Message too large"})
                            break
                        try:
                            msg = json.loads(line.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            owner._send(sock, {"type": "disconnect", "reason": "Malformed message"})
                            break
                        if not isinstance(msg, dict):
                            break
                        kind = msg.get("type")
                        if kind == "chat":
                            body = msg.get("message")
                            if not isinstance(body, str) or not 1 <= len(body) <= 256:
                                continue
                            packet = {"type": "chat", "username": username, "message": body}
                            owner.broadcast(packet)
                            owner._emit("chat", username=username, message=body)
                        elif kind == "player_state":
                            pos = msg.get("position")
                            if (not isinstance(pos, list) or len(pos) != 3
                                    or any(type(v) not in (int, float) for v in pos)):
                                continue
                            packet = {"type": "player_state", "username": username,
                                      "position": [float(v) for v in pos]}
                            owner.broadcast(packet, exclude=sock)
                        elif kind == "ping":
                            owner._send(sock, {"type": "pong", "nonce": msg.get("nonce")})
                        else:
                            owner._send(sock, {"type": "error", "reason": "Unknown message type"})
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, socket.timeout):
                    pass
                finally:
                    owner._drop(sock)

        self._stopping.clear()
        self._server = _ThreadingServer((self.config.host, self.config.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="PythonEditionServer", daemon=True)
        self._thread.start()
        return self.address

    def stop(self):
        server, thread = self._server, self._thread
        if server is None:
            return
        self._stopping.set()
        with self._lock:
            clients = tuple(self._clients)
        for sock in clients:
            self._drop(sock)
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        self._server = None
        self._thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.stop()
        return False


__all__ = ["PROTOCOL_VERSION", "MAX_MESSAGE_BYTES", "ServerError", "ServerConfig", "PythonEditionServer"]
