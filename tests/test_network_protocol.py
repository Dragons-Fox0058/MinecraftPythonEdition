"""Protocol 340 packet codec and handshake tests."""
import json
import struct
import unittest
from unittest.mock import patch
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import uuid

from engine.network.codec import (
    PacketBuffer, ProtocolError, encode_packet, decode_packet,
    encode_compressed_packet, decode_compressed_packet,
)
from engine.core import BlockPos, EnumFacing
from engine.network.packets import (
    serverbound_chat, serverbound_keep_alive, serverbound_position,
    serverbound_position_look, serverbound_held_item, serverbound_digging,
    decode_clientbound_keep_alive, decode_clientbound_chat,
    decode_clientbound_join_game, decode_clientbound_player_position_look,
    decode_clientbound_chunk_data,
)
from engine.network.login import login_offline, login_online, minecraft_server_hash
from engine.network.status import query_server
from engine.network.connection import (
    ConnectionState, decode_handshake, encode_handshake,
    encode_login_start, decode_status_response, MinecraftConnection,
)


class FakeSocket:
    def __init__(self, incoming=b""):
        self.incoming = bytearray(incoming)
        self.sent = bytearray()
        self.closed = False

    def recv(self, size):
        if not self.incoming:
            return b""
        result = bytes(self.incoming[:size])
        del self.incoming[:size]
        return result

    def sendall(self, data):
        self.sent.extend(data)

    def close(self):
        self.closed = True


class TestPacketBuffer(unittest.TestCase):
    def test_varint_signed_round_trip(self):
        for value in (0, 1, 127, 128, 255, 2147483647, -1, -2147483648):
            with self.subTest(value=value):
                writer = PacketBuffer()
                writer.write_varint(value)
                self.assertEqual(PacketBuffer(writer.to_bytes()).read_varint(), value)

    def test_varint_rejects_six_byte_encoding(self):
        with self.assertRaises(ProtocolError):
            PacketBuffer(b"\x80\x80\x80\x80\x80\x00").read_varint()

    def test_string_uuid_and_packed_position_round_trip(self):
        writer = PacketBuffer()
        writer.write_string("Minecraft 1.12.2")
        value = uuid.uuid4()
        writer.write_uuid(value)
        writer.write_position(-33554432, -2048, 33554431)
        reader = PacketBuffer(writer.to_bytes())
        self.assertEqual(reader.read_string(), "Minecraft 1.12.2")
        self.assertEqual(reader.read_uuid(), value)
        self.assertEqual(reader.read_position(), (-33554432, -2048, 33554431))
        self.assertEqual(reader.remaining, 0)

    def test_packet_frame_round_trip_and_bad_length(self):
        frame = encode_packet(0x23, b"payload")
        self.assertEqual(decode_packet(frame), (0x23, b"payload"))
        with self.assertRaises(ProtocolError):
            decode_packet(b"\x05\x01")

    def test_compression_round_trip_both_sides_of_threshold(self):
        for payload in (b"small", b"x" * 2048):
            frame = encode_compressed_packet(0x20, payload, 128)
            self.assertEqual(decode_compressed_packet(frame, 128), (0x20, payload))

    def test_compression_rejects_invalid_stream(self):
        with self.assertRaises(ProtocolError):
            decode_compressed_packet(b"\x04\x05bad", 1)


class TestProtocolHandshake(unittest.TestCase):
    def test_handshake_status_and_login(self):
        for state in (ConnectionState.STATUS, ConnectionState.LOGIN):
            frame = encode_handshake("localhost", 25565, state)
            packet_id, payload = decode_packet(frame)
            self.assertEqual(packet_id, 0)
            version, host, port, next_state = decode_handshake(payload)
            self.assertEqual((version, host, port, next_state),
                             (340, "localhost", 25565, state))

    def test_login_start_and_status_json(self):
        frame = encode_login_start("TestPlayer")
        packet_id, payload = decode_packet(frame)
        self.assertEqual(packet_id, 0)
        self.assertEqual(PacketBuffer(payload).read_string(16), "TestPlayer")
        self.assertEqual(decode_status_response(
            PacketBuffer().to_bytes() if False else _encode_string_payload(
                json.dumps({"version": {"name": "1.12.2", "protocol": 340}})
            )
        )["version"]["protocol"], 340)

    def test_online_login_rsa_session_join_and_aes_cfb8(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        public_key_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        shared_secret = bytes(range(16))
        verify_token = b"server-token"
        encryption_request = PacketBuffer()
        encryption_request.write_string("")
        encryption_request.write_varint(len(public_key_der))
        encryption_request.write(public_key_der)
        encryption_request.write_varint(len(verify_token))
        encryption_request.write(verify_token)

        player_uuid = uuid.uuid4()
        success = PacketBuffer()
        success.write_string(str(player_uuid))
        success.write_string("OnlineTest", max_chars=16)
        server_cipher = Cipher(
            algorithms.AES(shared_secret), modes.CFB8(shared_secret)
        ).encryptor()
        encrypted_success = server_cipher.update(
            encode_packet(0x02, success.to_bytes())
        )
        fake = FakeSocket(
            encode_packet(0x01, encryption_request.to_bytes()) + encrypted_success
        )
        connection = MinecraftConnection(fake)
        joined = []
        def session_join(token, profile, server_hash):
            joined.append((token, profile, server_hash))

        with patch("engine.network.login.MinecraftConnection.connect",
                   return_value=connection), patch(
                   "engine.network.login.secrets.token_bytes",
                   return_value=shared_secret):
            returned, identity = login_online(
                "localhost", 25565, "OnlineTest", "test-access-token",
                player_uuid, session_join,
            )
        self.assertIs(returned, connection)
        self.assertEqual(identity.player_uuid, player_uuid)
        self.assertEqual(joined[0][0], "test-access-token")
        self.assertEqual(joined[0][1], player_uuid)
        self.assertEqual(
            joined[0][2],
            minecraft_server_hash("", shared_secret, public_key_der),
        )

    def test_minecraft_server_hash_uses_signed_hex(self):
        self.assertEqual(
            minecraft_server_hash("", bytes(16), bytes.fromhex("010203")),
            __import__("hashlib").sha1(bytes(16) + bytes.fromhex("010203")).digest().hex().lstrip("0") or "0",
        )

    def test_offline_login_success(self):
        player_uuid = uuid.uuid4()
        payload = PacketBuffer()
        payload.write_string(str(player_uuid))
        payload.write_string("TestPlayer", max_chars=16)
        fake = FakeSocket(encode_packet(0x02, payload.to_bytes()))
        connection = MinecraftConnection(fake)
        with patch("engine.network.login.MinecraftConnection.connect",
                   return_value=connection):
            returned, identity = login_offline("localhost", 25565, "TestPlayer")
        self.assertIs(returned, connection)
        self.assertEqual(identity.player_uuid, player_uuid)
        self.assertEqual(identity.username, "TestPlayer")
        self.assertEqual(connection.state, ConnectionState.PLAY)

    def test_offline_login_rejects_online_mode_encryption(self):
        fake = FakeSocket(encode_packet(0x01, b""))
        connection = MinecraftConnection(fake)
        with patch("engine.network.login.MinecraftConnection.connect",
                   return_value=connection):
            with self.assertRaises(ProtocolError):
                login_offline("localhost", 25565, "TestPlayer")
        self.assertTrue(fake.closed)

    def test_clientbound_join_game_and_player_position_decoders(self):
        payload = PacketBuffer()
        payload.write(struct.pack(">iBiBB", 123, 1, -1, 2, 20))
        payload.write_string("default")
        payload.write(b"\x01")
        packet = decode_clientbound_join_game(payload.to_bytes())
        self.assertEqual(packet.entity_id, 123)
        self.assertEqual(packet.dimension, -1)
        self.assertEqual(packet.level_type, "default")
        self.assertTrue(packet.reduced_debug_info)

        position = struct.pack(">dddffB", 1.5, 64.0, -2.5, 90.0, 10.0, 3)
        teleport = PacketBuffer()
        teleport.write_varint(42)
        decoded = decode_clientbound_player_position_look(position + teleport.to_bytes())
        self.assertEqual((decoded.x, decoded.y, decoded.z), (1.5, 64.0, -2.5))
        self.assertEqual(decoded.teleport_id, 42)

    def test_clientbound_chunk_data_decoder(self):
        payload = struct.pack(">iiB", -2, 4, 1)
        bitmask = PacketBuffer()
        bitmask.write_varint(5)
        length = PacketBuffer()
        length.write_varint(4)
        raw = payload + bitmask.to_bytes() + length.to_bytes() + b"abcd" + b"tile-nbt"
        chunk = decode_clientbound_chunk_data(raw)
        self.assertEqual((chunk.chunk_x, chunk.chunk_z), (-2, 4))
        self.assertTrue(chunk.ground_up)
        self.assertEqual(chunk.primary_bitmask, 5)
        self.assertEqual(chunk.data, b"abcd")
        self.assertEqual(chunk.block_entities_payload, b"tile-nbt")

    def test_common_play_packet_payloads(self):
        packet_id, payload = serverbound_chat("hello")
        self.assertEqual(packet_id, 0x02)
        self.assertEqual(PacketBuffer(payload).read_string(100), "hello")

        packet_id, payload = serverbound_keep_alive(1234)
        self.assertEqual(packet_id, 0x0B)
        self.assertEqual(decode_clientbound_keep_alive(payload), 1234)

        packet_id, payload = serverbound_position(1.0, 64.0, -2.0, True)
        self.assertEqual(packet_id, 0x0D)
        self.assertEqual(struct.unpack(">ddd?", payload), (1.0, 64.0, -2.0, True))

        packet_id, payload = serverbound_position_look(1, 2, 3, 90, -20, False)
        self.assertEqual(packet_id, 0x0E)
        self.assertEqual(struct.unpack(">dddff?", payload), (1.0, 2.0, 3.0, 90.0, -20.0, False))

        packet_id, payload = serverbound_held_item(8)
        self.assertEqual((packet_id, struct.unpack(">h", payload)[0]), (0x19, 8))

        packet_id, payload = serverbound_digging(0, BlockPos(-1, 64, 2), EnumFacing.UP)
        self.assertEqual(packet_id, 0x13)
        reader = PacketBuffer(payload)
        self.assertEqual(reader.read_varint(), 0)
        self.assertEqual(reader.read_position(), (-1, 64, 2))
        self.assertEqual(reader.read(1), b"\x01")

        chat = PacketBuffer()
        chat.write_string('{"text":"hi"}')
        chat.write(b"\x01")
        self.assertEqual(decode_clientbound_chat(chat.to_bytes()), ('{"text":"hi"}', 1))

    def test_play_packet_validates_arguments(self):
        with self.assertRaises(ValueError):
            serverbound_chat("x" * 101)
        with self.assertRaises(ValueError):
            serverbound_held_item(9)
        with self.assertRaises(ValueError):
            serverbound_digging(7, BlockPos(0, 0, 0), EnumFacing.UP)

    def test_status_query_performs_status_and_ping_exchange(self):
        status = {"version": {"name": "1.12.2", "protocol": 340},
                  "players": {"max": 20, "online": 3},
                  "description": {"text": "Test server"}}
        status_payload = PacketBuffer()
        status_payload.write_string(json.dumps(status))
        stamp = 123456789
        pong_payload = struct.pack(">q", stamp)
        fake = FakeSocket(
            encode_packet(0x00, status_payload.to_bytes())
            + encode_packet(0x01, pong_payload)
        )
        connection = MinecraftConnection(fake)
        with patch("engine.network.status.MinecraftConnection.connect",
                   return_value=connection), patch("engine.network.status.time.time",
                   return_value=stamp / 1000):
            result = query_server("localhost", 25565)
        self.assertEqual(result.protocol, 340)
        self.assertEqual(result.online_players, 3)
        self.assertEqual(result.version_name, "1.12.2")
        self.assertTrue(fake.closed)

    def test_connection_receive_send_and_compression_switch(self):
        incoming = encode_packet(0x00, b"first")
        sock = FakeSocket(incoming)
        connection = MinecraftConnection(sock)
        self.assertEqual(connection.receive(), (0, b"first"))
        connection.send(0x01, b"reply")
        self.assertEqual(decode_packet(bytes(sock.sent)), (1, b"reply"))
        sock.sent.clear()
        connection.set_compression(64)
        connection.send(0x02, b"x" * 100)
        self.assertEqual(decode_compressed_packet(bytes(sock.sent), 64), (2, b"x" * 100))
        connection.close()
        self.assertTrue(sock.closed)


def _encode_string_payload(value):
    buffer = PacketBuffer()
    buffer.write_string(value)
    return buffer.to_bytes()


if __name__ == "__main__":
    unittest.main()
