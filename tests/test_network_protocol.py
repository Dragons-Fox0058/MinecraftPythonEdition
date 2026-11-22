"""Protocol 340 packet codec and handshake tests."""
import json
import struct
import unittest
import uuid

from engine.network.codec import (
    PacketBuffer, ProtocolError, encode_packet, decode_packet,
    encode_compressed_packet, decode_compressed_packet,
)
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
