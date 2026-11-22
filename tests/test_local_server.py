"""Tests for the Python Edition-only LAN host."""
import json
import socket
import unittest

from engine.server.local import PythonEditionServer, ServerConfig
from engine.network.python_edition import PythonEditionClient


class TestPythonEditionServer(unittest.TestCase):
    def test_python_client_can_join_and_exchange_chat(self):
        server = PythonEditionServer(ServerConfig(host="127.0.0.1", port=0))
        host, port = server.start()
        client = socket.create_connection((host, port), timeout=2)
        stream = client.makefile("rwb")
        try:
            stream.write(json.dumps({"type": "hello", "edition": "MinecraftPythonEdition",
                                     "protocol": 1, "username": "Tester"}).encode() + b"\n")
            stream.flush()
            welcome = json.loads(stream.readline())
            self.assertEqual(welcome["type"], "welcome")
            self.assertEqual(welcome["username"], "Tester")
            stream.write(json.dumps({"type": "ping", "nonce": 42}).encode() + b"\n")
            stream.flush()
            self.assertEqual(json.loads(stream.readline()), {"type": "pong", "nonce": 42})
            self.assertEqual(server.player_count, 1)
        finally:
            stream.close()
            client.close()
            server.stop()
        self.assertFalse(server.running)

    def test_java_client_is_rejected(self):
        server = PythonEditionServer(ServerConfig(host="127.0.0.1", port=0))
        host, port = server.start()
        client = socket.create_connection((host, port), timeout=2)
        stream = client.makefile("rwb")
        try:
            stream.write(b'{"type":"hello","edition":"Java","protocol":340,"username":"Nope"}\\n')
            stream.flush()
            response = json.loads(stream.readline())
            self.assertEqual(response["type"], "disconnect")
            self.assertIn("Python Edition", response["reason"])
            self.assertEqual(server.player_count, 0)
        finally:
            stream.close()
            client.close()
            server.stop()

    def test_python_edition_client_handshake(self):
        server = PythonEditionServer(ServerConfig(host="127.0.0.1", port=0))
        host, port = server.start()
        client = PythonEditionClient(host, port, "ClientTester")
        try:
            welcome = client.connect()
            self.assertEqual(welcome["type"], "welcome")
            self.assertEqual(welcome["username"], "ClientTester")
            self.assertEqual(server.player_count, 1)
            client.send_chat("hello")
            client.send_player_state(1.0, 64.0, -2.0)
        finally:
            client.close()
            server.stop()

    def test_config_rejects_invalid_port(self):
        with self.assertRaises(ValueError):
            ServerConfig(port=65536)


if __name__ == "__main__":
    unittest.main()
