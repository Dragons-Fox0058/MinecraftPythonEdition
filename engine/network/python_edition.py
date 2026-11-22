"""Python Edition LAN client for the dedicated local-host protocol."""
from __future__ import annotations

import json
import math
import queue
import socket
import threading

from engine.server.local import MAX_MESSAGE_BYTES, PROTOCOL_VERSION, ServerError


class PythonEditionClient:
    """Client for PythonEditionServer; intentionally not a Java protocol client."""

    def __init__(self, host: str, port: int, username: str, *, timeout: float = 5.0):
        if not isinstance(host, str) or not host:
            raise ValueError("host must be non-empty")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("port must be from 0 to 65535")
        if not isinstance(username, str) or not 1 <= len(username) <= 16:
            raise ValueError("username must contain 1..16 characters")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        self.host, self.port, self.username = host, port, username
        self.timeout = timeout
        self.socket = None
        self._reader = None
        self._thread = None
        self._stop = threading.Event()
        self._incoming = queue.Queue(maxsize=1024)
        self.welcome = None
        self.error = None

    @staticmethod
    def _encode(message: dict) -> bytes:
        raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ServerError("message exceeds size limit")
        return raw

    def connect(self) -> dict:
        if self.socket is not None:
            raise ServerError("client is already connected")
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        try:
            sock.sendall(self._encode({"type": "hello", "edition": "MinecraftPythonEdition",
                                       "protocol": PROTOCOL_VERSION, "username": self.username}))
            reader = sock.makefile("rb")
            line = reader.readline(MAX_MESSAGE_BYTES + 1)
            if not line or len(line) > MAX_MESSAGE_BYTES:
                raise ServerError("server closed before sending a welcome message")
            response = json.loads(line.decode("utf-8"))
            if not isinstance(response, dict) or response.get("type") != "welcome":
                reason = response.get("reason", "invalid server response") if isinstance(response, dict) else "invalid server response"
                raise ServerError(str(reason))
            if response.get("protocol") != PROTOCOL_VERSION:
                raise ServerError("server protocol version mismatch")
            sock.settimeout(None)
            self.socket, self._reader, self.welcome = sock, reader, response
            self._thread = threading.Thread(target=self._receive_loop,
                                            name="PythonEditionClientReceiver", daemon=True)
            self._thread.start()
            return response
        except Exception:
            try:
                sock.close()
            except OSError:
                pass
            raise

    def _receive_loop(self):
        try:
            while not self._stop.is_set():
                line = self._reader.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_MESSAGE_BYTES:
                    raise ServerError("server message exceeds size limit")
                message = json.loads(line.decode("utf-8"))
                if not isinstance(message, dict):
                    continue
                try:
                    self._incoming.put_nowait(message)
                except queue.Full:
                    raise ServerError("incoming message queue is full")
                if message.get("type") == "disconnect":
                    break
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ServerError) as exc:
            self.error = exc
        finally:
            self._stop.set()

    def _send(self, message: dict):
        if self.socket is None or self._stop.is_set():
            raise ServerError("client is not connected")
        self.socket.sendall(self._encode(message))

    def send_chat(self, message: str):
        if not isinstance(message, str) or not 1 <= len(message) <= 256:
            raise ValueError("chat message must contain 1..256 characters")
        self._send({"type": "chat", "message": message})

    def send_player_state(self, x: float, y: float, z: float):
        values = (x, y, z)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("player coordinates must be finite numbers")
        self._send({"type": "player_state", "position": [float(v) for v in values]})

    def poll(self, limit: int = 100) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        messages = []
        for _ in range(limit):
            try:
                messages.append(self._incoming.get_nowait())
            except queue.Empty:
                break
        return messages

    def close(self):
        self._stop.set()
        sock, reader = self.socket, self._reader
        self.socket = self._reader = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if reader is not None:
            try:
                reader.close()
            except OSError:
                pass
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


__all__ = ["PythonEditionClient"]
