"""Minecraft Java 1.12.2 server status ping client."""
from __future__ import annotations

import json
import socket
import struct
import time
from dataclasses import dataclass

from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import (
    ConnectionState, MinecraftConnection, decode_status_response,
)


@dataclass(frozen=True)
class ServerStatus:
    version_name: str
    protocol: int
    max_players: int
    online_players: int
    description: object
    raw: dict


def query_server(host: str, port: int = 25565, timeout: float = 5.0) -> ServerStatus:
    """Perform the vanilla status handshake, JSON query, and latency ping."""
    connection = MinecraftConnection.connect(host, port, timeout)
    try:
        connection.send_handshake(host, port, ConnectionState.STATUS)
        connection.send(0x00)
        packet_id, payload = connection.receive()
        if packet_id != 0x00:
            raise ProtocolError(f"expected status response, received packet {packet_id}")
        response = decode_status_response(payload)
        try:
            version = response["version"]
            players = response["players"]
            result = ServerStatus(
                str(version["name"]), int(version["protocol"]),
                int(players["max"]), int(players["online"]),
                response.get("description"), response,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProtocolError("status JSON is missing required fields") from exc

        stamp = int(time.time() * 1000)
        ping = PacketBuffer()
        ping.write(struct.pack(">q", stamp))
        connection.send(0x01, ping.to_bytes())
        pong_id, pong_payload = connection.receive()
        if pong_id != 0x01 or len(pong_payload) != 8:
            raise ProtocolError("invalid status pong packet")
        if struct.unpack(">q", pong_payload)[0] != stamp:
            raise ProtocolError("status pong payload did not match ping")
        return result
    finally:
        connection.close()


__all__ = ["ServerStatus", "query_server"]
