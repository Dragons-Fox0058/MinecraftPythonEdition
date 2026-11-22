"""Desktop first-person world preview with Python Edition LAN controls."""
from __future__ import annotations

import math
import time

from engine.input.state import InputState
from engine.render.camera import Camera
from engine.render.mesh import ChunkMeshBuilder
from engine.render.opengl import OpenGLRenderer
from engine.worldgen.generator import ChunkGeneratorOverworld
from engine.server.local import PythonEditionServer, ServerConfig
from engine.network.python_edition import PythonEditionClient


def main(*, seed: int = 0) -> None:
    """Open a generated chunk preview.

    WASD moves, Space/Ctrl moves vertically, Shift accelerates, mouse looks,
    F6 toggles a Python Edition LAN host, F7 joins one, Escape closes.
    """
    try:
        import glfw
    except ImportError as exc:
        raise RuntimeError("Desktop mode requires glfw and PyOpenGL; install requirements.txt") from exc

    chunk = ChunkGeneratorOverworld(int(seed)).generate_chunk(0, 0)
    mesh = ChunkMeshBuilder().build(chunk)
    camera = Camera(position=(8.0, 92.0, -12.0), yaw=0.0, pitch=28.0)
    input_state = InputState()
    lan_server = None
    lan_client = None

    with OpenGLRenderer(1280, 720) as renderer:
        window = renderer.window
        glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        def on_key(_window, key, _scancode, action, _mods):
            nonlocal lan_server, lan_client
            if action == glfw.PRESS:
                input_state.key_down(key)
                if key == glfw.KEY_ESCAPE:
                    glfw.set_window_should_close(window, True)
                elif key == glfw.KEY_F6:
                    try:
                        if lan_server is not None and lan_server.running:
                            lan_server.stop()
                            lan_server = None
                            glfw.set_window_title(window, "Minecraft Python Edition")
                        else:
                            lan_server = PythonEditionServer(ServerConfig(host="0.0.0.0", port=25575))
                            _host, port = lan_server.start()
                            glfw.set_window_title(window, f"Minecraft Python Edition — LAN HOST :{port}")
                            print(f"[LAN] Python Edition server listening on port {port}")
                    except Exception as exc:
                        lan_server = None
                        print(f"[LAN] Could not start/stop server: {exc}")
                elif key == glfw.KEY_F7:
                    try:
                        import tkinter as tk
                        from tkinter import simpledialog
                        dialog = tk.Tk()
                        dialog.withdraw()
                        address = simpledialog.askstring("Join Python Edition", "Server address (host:port):", parent=dialog)
                        username = simpledialog.askstring("Player name", "Username (1-16 characters):", parent=dialog)
                        dialog.destroy()
                        if address and username:
                            host, port_text = address.rsplit(":", 1)
                            candidate = PythonEditionClient(host.strip(), int(port_text), username.strip())
                            candidate.connect()
                            if lan_client is not None:
                                lan_client.close()
                            lan_client = candidate
                            glfw.set_window_title(window, f"Minecraft Python Edition — {host}:{port_text}")
                            print(f"[LAN] Connected as {username.strip()}")
                    except Exception as exc:
                        print(f"[LAN] Join failed: {exc}")
            elif action == glfw.RELEASE:
                input_state.key_up(key)

        def on_mouse(_window, x, y):
            if input_state.mouse_x == 0.0 and input_state.mouse_y == 0.0:
                input_state.mouse_x, input_state.mouse_y = x, y
                return
            input_state.mouse_move(x, y)

        glfw.set_key_callback(window, on_key)
        glfw.set_cursor_pos_callback(window, on_mouse)
        renderer.upload_chunk_mesh((0, 0), mesh)
        previous = time.perf_counter()
        network_send_timer = 0.0
        try:
            while not renderer.should_close():
                now = time.perf_counter()
                dt = min(now - previous, 0.05)
                previous = now
                speed = 18.0 if input_state.is_key_down(glfw.KEY_LEFT_SHIFT) else 6.0
                right = float(input_state.is_key_down(glfw.KEY_D)) - float(input_state.is_key_down(glfw.KEY_A))
                forward = float(input_state.is_key_down(glfw.KEY_W)) - float(input_state.is_key_down(glfw.KEY_S))
                up = float(input_state.is_key_down(glfw.KEY_SPACE)) - float(input_state.is_key_down(glfw.KEY_LEFT_CONTROL))
                length = math.hypot(right, forward)
                if length > 0:
                    right, forward = right / length, forward / length
                camera.move_local(right=right * speed * dt, up=up * speed * dt,
                                  forward=forward * speed * dt)
                camera.rotate(-input_state.mouse_dx * 0.12, input_state.mouse_dy * 0.12)

                if lan_client is not None:
                    for message in lan_client.poll():
                        if message.get("type") in ("chat", "player_joined", "player_left", "disconnect"):
                            print(f"[LAN] {message}")
                    network_send_timer += dt
                    if network_send_timer >= 0.1:
                        network_send_timer = 0.0
                        try:
                            lan_client.send_player_state(*camera.position.tolist())
                        except Exception as exc:
                            print(f"[LAN] Connection lost: {exc}")
                            lan_client.close()
                            lan_client = None

                # Clear deltas only after consuming them; render() polls GLFW at frame end.
                input_state.begin_frame()
                width, height = glfw.get_framebuffer_size(window)
                if width > 0 and height > 0:
                    renderer.gl.glViewport(0, 0, width, height)
                    renderer.render(camera.view_projection_matrix(width / height))
        finally:
            if lan_client is not None:
                lan_client.close()
            if lan_server is not None:
                lan_server.stop()


if __name__ == "__main__":
    main()
