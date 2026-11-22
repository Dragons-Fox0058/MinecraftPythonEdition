"""Protocol-340 play packet tests."""
import json
import struct
import unittest

from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.play import (
    CLIENTBOUND, SERVERBOUND, PlayPacketDispatcher, create_clientbound_dispatcher,
    serverbound_teleport_confirm, serverbound_client_status,
    serverbound_client_settings, decode_block_change, decode_unload_chunk,
    decode_disconnect, decode_update_health, decode_time_update,
    decode_player_abilities, decode_respawn, decode_plugin_message,
    decode_change_game_state,
)


class TestPlayPackets(unittest.TestCase):
    def test_serverbound_teleport_confirm(self):
        packet_id, payload = serverbound_teleport_confirm(123)
        self.assertEqual(packet_id, SERVERBOUND["teleport_confirm"])
        self.assertEqual(PacketBuffer(payload).read_varint(), 123)

    def test_serverbound_client_status(self):
        packet_id, payload = serverbound_client_status(1)
        self.assertEqual(packet_id, SERVERBOUND["client_status"])
        self.assertEqual(PacketBuffer(payload).read_varint(), 1)

    def test_serverbound_client_settings(self):
        packet_id, payload = serverbound_client_settings()
        self.assertEqual(packet_id, SERVERBOUND["client_settings"])
        buf = PacketBuffer(payload)
        self.assertEqual(buf.read_string(16), "en_US")
        self.assertEqual(struct.unpack(">b", buf.read(1))[0], 10)
        self.assertEqual(buf.read_varint(), 0)
        self.assertEqual(buf.read(2), bytes((1, 0x7F)))
        self.assertEqual(buf.read_varint(), 1)
        self.assertEqual(buf.remaining, 0)

    def test_serverbound_validates(self):
        for call in (
            lambda: serverbound_teleport_confirm(-1),
            lambda: serverbound_client_status(4),
            lambda: serverbound_client_settings(view_distance=33),
            lambda: serverbound_client_settings(chat_mode=3),
            lambda: serverbound_client_settings(main_hand=2),
        ):
            with self.assertRaises((ValueError, TypeError)):
                call()

    def test_block_change(self):
        buf = PacketBuffer()
        buf.write_position(-12, 64, 20)
        buf.write_varint(1234)
        result = decode_block_change(buf.to_bytes())
        self.assertEqual((result.x, result.y, result.z, result.state_id),
                         (-12, 64, 20, 1234))

    def test_unload_chunk(self):
        self.assertEqual(decode_unload_chunk(struct.pack(">ii", -2, 3)).chunk_x, -2)
        with self.assertRaises(ProtocolError):
            decode_unload_chunk(b"bad")

    def test_disconnect(self):
        buf = PacketBuffer()
        buf.write_string(json.dumps({"text": "Disconnected"}))
        self.assertEqual(decode_disconnect(buf.to_bytes()).reason["text"], "Disconnected")
        with self.assertRaises(ProtocolError):
            decode_disconnect(b"\x01x")

    def test_health_time_and_abilities(self):
        food = PacketBuffer()
        food.write_varint(17)
        health = decode_update_health(struct.pack(">f", 18.5) + food.to_bytes() + struct.pack(">f", 4.0))
        self.assertEqual((health.health, health.food, health.food_saturation),
                         (18.5, 17, 4.0))
        time = decode_time_update(struct.pack(">qq", 1000, 6000))
        self.assertEqual((time.world_age, time.time_of_day), (1000, 6000))
        abilities = decode_player_abilities(struct.pack(">Bff", 0x05, 0.05, 0.1))
        self.assertEqual(abilities.flags, 0x05)
        with self.assertRaises(ProtocolError):
            decode_player_abilities(struct.pack(">Bff", 0x80, 0.05, 0.1))

    def test_respawn_plugin_message_and_game_state(self):
        respawn = struct.pack(">iBB", -1, 2, 1) + _string("default")
        result = decode_respawn(respawn)
        self.assertEqual((result.dimension, result.difficulty, result.game_mode), (-1, 2, 1))
        plugin = _string("MC|Brand") + b"vanilla"
        message = decode_plugin_message(plugin)
        self.assertEqual((message.channel, message.data), ("MC|Brand", b"vanilla"))
        state = decode_change_game_state(struct.pack(">Bf", 3, 1.0))
        self.assertEqual((state.reason, state.value), (3, 1.0))
        with self.assertRaises(ProtocolError):
            decode_change_game_state(b"bad")

    def test_dispatcher_known_and_unknown_packets(self):
        dispatcher = create_clientbound_dispatcher()
        buf = PacketBuffer()
        buf.write_position(1, 2, 3)
        buf.write_varint(5)
        result = dispatcher.dispatch(CLIENTBOUND["block_change"], buf.to_bytes())
        self.assertEqual(result.state_id, 5)
        self.assertIsNone(dispatcher.dispatch(0x7F, b"opaque"))
        custom = PlayPacketDispatcher()
        custom.register(1, lambda data: data.upper())
        self.assertEqual(custom.dispatch(1, b"abc"), b"ABC")
        with self.assertRaises(ValueError):
            custom.register(1, lambda data: data)


def _string(value):
    buf = PacketBuffer()
    buf.write_string(value)
    return buf.to_bytes()


if __name__ == "__main__":
    unittest.main()
