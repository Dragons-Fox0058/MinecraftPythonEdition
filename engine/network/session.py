"""Basic client play-state integration for the implemented protocol-340 packets."""
from __future__ import annotations

from engine.core import BlockPos
from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.connection import ConnectionState
from engine.network.packets import (
    decode_clientbound_chat, decode_clientbound_chunk_data,
    decode_clientbound_join_game, decode_clientbound_keep_alive,
    decode_clientbound_player_position_look,
)
from engine.network.play import (
    CLIENTBOUND, decode_block_change, decode_disconnect, decode_player_abilities,
    decode_time_update, decode_unload_chunk, decode_update_health,
    serverbound_teleport_confirm,
)


class PlaySession:
    """Routes a deliberately supported subset of server play packets.

    Unsupported packet IDs are surfaced to the event callback as opaque bytes;
    they are not silently interpreted as another packet type.
    """

    def __init__(self, connection, *, world=None, player=None, on_event=None):
        if not hasattr(connection, "receive") or not hasattr(connection, "send"):
            raise TypeError("connection must provide receive() and send()")
        self.connection = connection
        self.world = world
        self.player = player
        self.on_event = on_event
        self.connected = True
        self.join_game = None
        self.last_chat = None
        self.last_disconnect = None
        self.last_health = None
        self.last_time = None
        self.last_abilities = None
        self.last_teleport = None

    def _emit(self, name: str, value):
        if self.on_event is not None:
            self.on_event(name, value)
        return value

    def process_packet(self, packet_id: int, payload: bytes):
        if not self.connected:
            raise RuntimeError("play session is disconnected")

        if packet_id == CLIENTBOUND["keep_alive"]:
            keep_alive_id = decode_clientbound_keep_alive(payload)
            response = PacketBuffer()
            response.write_varint(keep_alive_id)
            self.connection.send(0x0B, response.to_bytes())
            return self._emit("keep_alive", keep_alive_id)

        if packet_id == CLIENTBOUND["join_game"]:
            self.join_game = decode_clientbound_join_game(payload)
            return self._emit("join_game", self.join_game)

        if packet_id == CLIENTBOUND["player_position_look"]:
            self.last_teleport = decode_clientbound_player_position_look(payload)
            packet, body = serverbound_teleport_confirm(self.last_teleport.teleport_id)
            self.connection.send(packet, body)
            return self._emit("teleport", self.last_teleport)

        if packet_id == CLIENTBOUND["block_change"]:
            change = decode_block_change(payload)
            if self.world is not None:
                self.world.set_block_state_id(
                    BlockPos(change.x, change.y, change.z), change.state_id
                )
            return self._emit("block_change", change)

        if packet_id == CLIENTBOUND["unload_chunk"]:
            chunk = decode_unload_chunk(payload)
            if self.world is not None:
                self.world.chunk_provider.unload(chunk.chunk_x, chunk.chunk_z)
            return self._emit("unload_chunk", chunk)

        if packet_id == CLIENTBOUND["chat"]:
            self.last_chat = decode_clientbound_chat(payload)
            return self._emit("chat", self.last_chat)

        if packet_id == CLIENTBOUND["disconnect"]:
            self.last_disconnect = decode_disconnect(payload)
            self.connected = False
            self.connection.close()
            return self._emit("disconnect", self.last_disconnect)

        if packet_id == CLIENTBOUND["update_health"]:
            self.last_health = decode_update_health(payload)
            if self.player is not None and hasattr(self.player, "health"):
                self.player.health = self.last_health.health
            return self._emit("health", self.last_health)

        if packet_id == CLIENTBOUND["time_update"]:
            self.last_time = decode_time_update(payload)
            return self._emit("time", self.last_time)

        if packet_id == CLIENTBOUND["player_abilities"]:
            self.last_abilities = decode_player_abilities(payload)
            return self._emit("abilities", self.last_abilities)

        if packet_id == CLIENTBOUND["chunk_data"]:
            chunk = decode_clientbound_chunk_data(payload)
            return self._emit("chunk_data", chunk)

        return self._emit("unknown_packet", (packet_id, bytes(payload)))

    def process_next(self):
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        packet_id, payload = self.connection.receive()
        return self.process_packet(packet_id, payload)

    def close(self):
        if self.connected:
            self.connected = False
            self.connection.close()


__all__ = ["PlaySession"]
