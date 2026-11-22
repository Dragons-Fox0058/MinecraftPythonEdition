"""Tests for protocol-340 play-session state integration."""
import json
import struct
import unittest
import uuid

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
        body.write(struct.pack(">q", 7654))
        result = session.process_packet(CLIENTBOUND["keep_alive"], body.to_bytes())
        self.assertEqual(result, 7654)
        self.assertEqual(conn.sent[0][0], 0x0B)
        self.assertEqual(struct.unpack(">q", conn.sent[0][1])[0], 7654)

    def test_block_change_updates_world(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        body = PacketBuffer()
        body.write_position(-3, 70, 8)
        body.write_varint(42)
        session.process_packet(CLIENTBOUND["block_change"], body.to_bytes())
        self.assertEqual(world.get_block_state_id(BlockPos(-3, 70, 8)), 42)

    def test_multi_block_change_updates_world(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        body = PacketBuffer()
        body.write(struct.pack(">ii", -2, 3))
        body.write_varint(2)
        body.write(bytes((0xA5, 64)))
        body.write_varint(17)
        body.write(bytes((0x0F, 70)))
        body.write_varint(33)
        session.process_packet(CLIENTBOUND["multi_block_change"], body.to_bytes())
        self.assertEqual(world.get_block_state_id(BlockPos(-22, 64, 53)), 17)
        self.assertEqual(world.get_block_state_id(BlockPos(-32, 70, 63)), 33)

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

    def test_join_game_sends_client_settings(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        body = PacketBuffer()
        body.write(struct.pack(">iBiBB", 44, 1, -1, 2, 20))
        body.write_string("default")
        body.write(bytes((0,)))
        result = session.process_packet(CLIENTBOUND["join_game"], body.to_bytes())
        self.assertEqual(result.entity_id, 44)
        self.assertEqual(world.dimension, -1)
        self.assertEqual(conn.sent[0][0], 0x04)

    def test_teleport_applies_relative_coordinates(self):
        conn = FakeConnection()
        player = EntityPlayer(World())
        player.set_position(10, 20, 30)
        player.yaw, player.pitch = 15, 5
        session = PlaySession(conn, player=player)
        body = PacketBuffer()
        body.write(struct.pack(">dddffB", 1, 2, 3, 10, 20, 0x1F))
        body.write_varint(7)
        session.process_packet(CLIENTBOUND["player_position_look"], body.to_bytes())
        self.assertEqual((player.pos.x, player.pos.y, player.pos.z), (11, 22, 33))
        self.assertEqual((player.yaw, player.pitch), (25, 25))
        self.assertEqual(conn.sent[0][0], 0x00)

    def test_health_and_time_are_applied(self):
        conn = FakeConnection()
        world = World()
        player = EntityPlayer(world)
        player.hunger = HungerManager()
        session = PlaySession(conn, world=world, player=player)
        food = PacketBuffer()
        food.write_varint(13)
        session.process_packet(CLIENTBOUND["update_health"],
                               struct.pack(">f", 17.5) + food.to_bytes() + struct.pack(">f", 3.0))
        self.assertEqual(player.health, 17.5)
        self.assertEqual(player.hunger.food_level, 13)
        self.assertEqual(player.hunger.saturation, 3.0)
        session.process_packet(CLIENTBOUND["time_update"], struct.pack(">qq", 900, 12345))
        self.assertEqual(world.world_time.total_time, 900)
        self.assertEqual(world.world_time.day_time, 12345)

    def test_remote_entity_spawn_move_velocity_and_destroy(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        entity_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        spawn = PacketBuffer()
        spawn.write_varint(77)
        spawn.write(entity_uuid.bytes)
        spawn.write(bytes((2,)))
        spawn.write(struct.pack(">ddd", 1.0, 2.0, 3.0))
        spawn.write(bytes((64, 128)))
        spawn.write(struct.pack(">i", 1))
        spawn.write(struct.pack(">hhh", 800, -400, 0))
        session.process_packet(CLIENTBOUND["spawn_object"], spawn.to_bytes())
        entity = session.network_entities[77]
        self.assertEqual((entity.pos.x, entity.pos.y, entity.pos.z), (1.0, 2.0, 3.0))
        self.assertEqual(entity.entity_uuid, entity_uuid)
        self.assertEqual(len(world.entities), 1)

        movement = PacketBuffer()
        movement.write_varint(77)
        movement.write(struct.pack(">hhh", 4096, 0, -4096))
        movement.write(bytes((1,)))
        session.process_packet(CLIENTBOUND["entity_relative_move"], movement.to_bytes())
        self.assertEqual((entity.pos.x, entity.pos.y, entity.pos.z), (2.0, 2.0, 2.0))
        self.assertTrue(entity.on_ground)

        velocity = PacketBuffer()
        velocity.write_varint(77)
        velocity.write(struct.pack(">hhh", 800, 0, -800))
        session.process_packet(CLIENTBOUND["entity_velocity"], velocity.to_bytes())
        self.assertAlmostEqual(entity.motion.x, 0.1)
        self.assertAlmostEqual(entity.motion.z, -0.1)

        teleport = PacketBuffer()
        teleport.write_varint(77)
        teleport.write(struct.pack(">ddd", 9.0, 8.0, 7.0))
        teleport.write(bytes((0, 64, 1)))
        session.process_packet(CLIENTBOUND["entity_teleport"], teleport.to_bytes())
        self.assertEqual((entity.pos.x, entity.pos.y, entity.pos.z), (9.0, 8.0, 7.0))

        destroy = PacketBuffer()
        destroy.write_varint(1)
        destroy.write_varint(77)
        session.process_packet(CLIENTBOUND["destroy_entities"], destroy.to_bytes())
        self.assertNotIn(77, session.network_entities)
        self.assertEqual(world.entities, [])

    def test_chunk_data_updates_loaded_world_chunk(self):
        conn = FakeConnection()
        world = World()
        session = PlaySession(conn, world=world)
        section = PacketBuffer()
        section.write(bytes((4,)))
        section.write_varint(1)
        section.write_varint(1)
        section.write_varint(256)
        section.write(struct.pack(">Q", 0) * 256)
        section.write(bytes([0x21]) * 2048)
        section.write(bytes([0x43]) * 2048)
        section.write(bytes([7]) * 256)
        body = PacketBuffer()
        body.write(struct.pack(">iiB", -2, 4, 1))
        body.write_varint(1)
        body.write_varint(len(section.to_bytes()))
        body.write(section.to_bytes())
        body.write_varint(0)
        session.process_packet(CLIENTBOUND["chunk_data"], body.to_bytes())
        chunk = world.chunk_provider.get_chunk(-2, 4)
        self.assertIsNotNone(chunk)
        self.assertEqual(int(chunk.blocks[0, 0, 0]), 1)
        self.assertEqual(int(chunk.blocks[15, 15, 15]), 1)
        self.assertEqual(int(chunk.light[0, 0, 0]), 0x31)
        self.assertEqual(int(chunk.light[1, 0, 0]), 0x42)
        self.assertEqual(int(chunk.biomes[0, 0]), 7)
        self.assertTrue(chunk.dirty)

    def test_send_player_state_selects_minimal_packet(self):
        conn = FakeConnection()
        player = EntityPlayer(World())
        session = PlaySession(conn, player=player)
        session.send_player_state(force=True)
        self.assertEqual(conn.sent[-1][0], 0x0E)
        player.set_position(1, 2, 3)
        session.send_player_state()
        self.assertEqual(conn.sent[-1][0], 0x0D)
        player.yaw = 45
        session.send_player_state()
        self.assertEqual(conn.sent[-1][0], 0x0F)
        session.send_player_state()
        self.assertEqual(conn.sent[-1][0], 0x0C)


if __name__ == "__main__":
    unittest.main()
