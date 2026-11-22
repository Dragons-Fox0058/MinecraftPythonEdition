"""Online-mode protocol 340 login with injected session authentication."""
from __future__ import annotations

import hashlib
import json
import uuid
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass

from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import (
    ConnectionState, MinecraftConnection, encode_login_start,
)


def _read_login_packet(connection: MinecraftConnection, username: str):
    while True:
        packet_id, payload = connection.receive()
        if packet_id == 0x03:
            buffer = PacketBuffer(payload)
            threshold = buffer.read_varint()
            if buffer.remaining:
                raise ProtocolError("trailing Set Compression payload")
            connection.set_compression(threshold)
            continue
        if packet_id == 0x00:
            buffer = PacketBuffer(payload)
            reason = buffer.read_string()
            try:
                reason = json.loads(reason)
            except json.JSONDecodeError:
                pass
            raise ProtocolError(f"login rejected: {reason}")
        if packet_id == 0x01:
            raise ProtocolError("unexpected second encryption request")
        if packet_id == 0x02:
            buffer = PacketBuffer(payload)
            raw_uuid = buffer.read_string(max_chars=36)
            accepted_name = buffer.read_string(max_chars=16)
            if buffer.remaining:
                raise ProtocolError("trailing Login Success payload")
            try:
                player_uuid = uuid.UUID(raw_uuid)
            except ValueError as exc:
                raise ProtocolError("invalid Login Success UUID") from exc
            if accepted_name != username:
                raise ProtocolError("server returned a different username")
            connection.state = ConnectionState.PLAY
            return LoginIdentity(player_uuid, accepted_name)
        raise ProtocolError(f"unexpected login packet ID: {packet_id}")


def minecraft_server_hash(server_id: str, shared_secret: bytes,
                          public_key_der: bytes) -> str:
    """Return Minecraft's signed SHA-1 server hash in Java BigInteger hex form."""
    digest = hashlib.sha1(server_id.encode("ascii") + shared_secret + public_key_der).digest()
    value = int.from_bytes(digest, "big", signed=True)
    return ("-" if value < 0 else "") + format(abs(value), "x")


def mojang_session_join(access_token: str, profile_uuid: uuid.UUID,
                        server_hash: str, timeout: float = 10.0) -> None:
    """Join an online-mode server using a launcher-issued access token."""
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("access_token must be non-empty")
    if not isinstance(profile_uuid, uuid.UUID):
        profile_uuid = uuid.UUID(str(profile_uuid))
    body = json.dumps({
        "accessToken": access_token,
        "selectedProfile": profile_uuid.hex,
        "serverId": server_hash,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://sessionserver.mojang.com/session/minecraft/join",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 204:
                raise ProtocolError(f"session join returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise ProtocolError(f"session authentication rejected (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise ProtocolError("could not reach the Minecraft session service") from exc


def login_online(host: str, port: int, username: str, access_token: str,
                 profile_uuid: uuid.UUID,
                 session_join, timeout: float = 10.0):
    """Online-mode login.

    session_join(access_token, profile_uuid, server_hash) must perform the
    authenticated session join operation and raise on rejection. The token is
    only passed to this callback and is never logged or persisted here.
    """
    if not isinstance(profile_uuid, uuid.UUID):
        profile_uuid = uuid.UUID(str(profile_uuid))
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("a valid launcher access token is required")
    if not callable(session_join):
        raise TypeError("session_join callback is required")

    connection = MinecraftConnection.connect(host, port, timeout)
    try:
        connection.send_handshake(host, port, ConnectionState.LOGIN)
        connection.send(0x00, _login_start_payload(username))
        while True:
            packet_id, payload = connection.receive()
            if packet_id == 0x03:
                buffer = PacketBuffer(payload)
                threshold = buffer.read_varint()
                if buffer.remaining:
                    raise ProtocolError("trailing Set Compression payload")
                connection.set_compression(threshold)
                continue
            if packet_id == 0x00:
                buffer = PacketBuffer(payload)
                raise ProtocolError(f"login rejected: {buffer.read_string()}")
            if packet_id != 0x01:
                if packet_id == 0x02:
                    raise ProtocolError(
                        "online-mode login success arrived before encryption; refusing unauthenticated login"
                    )
                raise ProtocolError(f"unexpected login packet ID: {packet_id}")
            request = PacketBuffer(payload)
            server_id = request.read_string(max_chars=20)
            key_length = request.read_varint()
            if not 1 <= key_length <= 8192:
                raise ProtocolError("invalid server public-key length")
            public_key_der = request.read(key_length)
            token_length = request.read_varint()
            if not 1 <= token_length <= 1024:
                raise ProtocolError("invalid encryption verify-token length")
            verify_token = request.read(token_length)
            if request.remaining:
                raise ProtocolError("trailing Encryption Request payload")

            try:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import padding
            except ImportError as exc:
                raise RuntimeError("online-mode login requires the cryptography package") from exc

            try:
                public_key = serialization.load_der_public_key(public_key_der)
                shared_secret = secrets.token_bytes(16)
                encrypted_secret = public_key.encrypt(shared_secret, padding.PKCS1v15())
                encrypted_token = public_key.encrypt(verify_token, padding.PKCS1v15())
            except Exception as exc:
                raise ProtocolError("invalid server RSA public key") from exc

            server_hash = minecraft_server_hash(server_id, shared_secret, public_key_der)
            session_join(access_token, profile_uuid, server_hash)

            response = PacketBuffer()
            response.write_varint(len(encrypted_secret))
            response.write(encrypted_secret)
            response.write_varint(len(encrypted_token))
            response.write(encrypted_token)
            connection.send(0x01, response.to_bytes())
            connection.enable_encryption(shared_secret)
            identity = _read_login_packet(connection, username)
            if identity.player_uuid != profile_uuid:
                raise ProtocolError("authenticated UUID does not match selected profile")
            connection.set_timeout(None)
            return connection, identity
    except Exception:
        connection.close()
        raise


def _login_start_payload(username: str) -> bytes:
    if not isinstance(username, str) or not 1 <= len(username) <= 16:
        raise ValueError("username must contain 1..16 characters")
    buffer = PacketBuffer()
    buffer.write_string(username, max_chars=16)
    return buffer.to_bytes()


@dataclass(frozen=True)
class LoginIdentity:
    player_uuid: uuid.UUID
    username: str


def login_offline(host: str, port: int, username: str, timeout: float = 10.0):
    """Log into an offline-mode 1.12.2 server and return (connection, identity)."""
    connection = MinecraftConnection.connect(host, port, timeout)
    try:
        connection.send_handshake(host, port, ConnectionState.LOGIN)
        connection.send(0x00, _login_start_payload(username))
        identity = _read_login_packet(connection, username)
        connection.set_timeout(None)
        return connection, identity
    except Exception:
        connection.close()
        raise


__all__ = ["LoginIdentity", "login_offline", "login_online", "minecraft_server_hash", "mojang_session_join"]
