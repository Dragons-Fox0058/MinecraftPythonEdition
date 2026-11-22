"""Tests for protocol-340 play-session state integration."""
import json
import struct
import unittest

from engine.entities.player import EntityPlayer
from engine.gameplay.health import HungerManager

from engine.core import BlockPos, ChunkPos
from engine.network.codec import PacketBuffer
from engine.network.play import CLIENTBOUND
from engine.network.session import PlaySession
from engine.world.world import World


class FakeConnection:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.incoming = []

    def send(self, packet_id, payload=b""):
        self.sent.append((packet_id, payload))

    def receive(self):
        return self.incoming.pop(0)

    def close(self):
        self.closed = True


class TestPlaySession(unittest.TestCase):
    def test_keep_alive_is_answered(self):
        conn = FakeConnection()
        session = PlaySession(conn)
        body = PacketBuffer()
        body.write_varint(7654)
        result = session.process_packet(CLIENTBOUND["keep_alive"], body.to_bytes())
        self.assertEqual(result, 7654)
        self.assertEqual(conn.sent[0][0], 0x0B)
        self.assertEqual(PacketBuffer(conn.sent[0][1]).read_varint(), 7654)

    def test_block_change_updates_world(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        body = PacketBuffer()
        body.write_position(-3, 70, 8)
        body.write_varint(42)
        session.process_packet(CLIENTBOUND["block_change"], body.to_bytes())
        self.assertEqual(world.get_block_state_id(BlockPos(-3, 70, 8)), 42)

    def test_unload_chunk_updates_world(self):
        conn = FakeConnection()
        world = World()
        world.chunk_provider.get_or_create(-1, 2)
        session = PlaySession(conn, world=world)
        session.process_packet(CLIENTBOUND["unload_chunk"], struct.pack(">ii", -1, 2))
        self.assertFalse(world.chunk_provider.has_chunk(-1, 2))

    def test_teleport_is_acknowledged(self):
        conn = FakeConnection()
        session = PlaySession(conn)
        body = PacketBuffer()
        body.write(struct.pack(">dddffB", 1.0, 65.0, 2.0, 90.0, 0.0, 0))
        body.write_varint(91)
        session.process_packet(CLIENTBOUND["player_position_look"], body.to_bytes())
        self.assertEqual(conn.sent[0][0], 0x00)
        self.assertEqual(PacketBuffer(conn.sent[0][1]).read_varint(), 91)

    def test_disconnect_closes_session(self):
        conn = FakeConnection()
        session = PlaySession(conn)
        body = PacketBuffer()
        body.write_string(json.dumps({"text": "Bye"}))
        result = session.process_packet(CLIENTBOUND["disconnect"], body.to_bytes())
        self.assertEqual(result.reason["text"], "Bye")
        self.assertFalse(session.connected)
        self.assertTrue(conn.closed)
        with self.assertRaises(RuntimeError):
            session.process_next()

    def test_unknown_packet_is_preserved(self):
        session = PlaySession(FakeConnection())
        self.assertEqual(session.process_packet(0x7F, b"opaque"), (0x7F, b"opaque"))


if __name__ == "__main__":
    unittest.main()
