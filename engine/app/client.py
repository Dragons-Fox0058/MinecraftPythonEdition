"""Desktop single-player survival foundation with Python Edition LAN controls."""
from __future__ import annotations

import math
import time

import numpy as np

from engine.core import Vec3d
from engine.entities.entity import Entity
from engine.input.state import InputState
from engine.network.python_edition import PythonEditionClient
from engine.render.camera import Camera
from engine.render.mesh import ChunkMeshBuilder
from engine.render.opengl import OpenGLRenderer
from engine.server.local import PythonEditionServer, ServerConfig
from engine.world.world import World
from engine.worldgen.generator import ChunkGeneratorOverworld


TICK_RATE = 20.0
PLAYER_WALK_SPEED = 4.3
PLAYER_SPRINT_SPEED = 5.6
PLAYER_JUMP_VELOCITY = 0.42


def _surface_y(chunk, local_x: int, local_z: int) -> int:
    """Return the highest non-air block at a local column."""
    for y in range(255, -1, -1):
        if chunk.get_block_state_id(local_x, y, local_z) != 0:
            return y
    return 0


def main(*, seed: int = 0) -> None:
    """Open the desktop world.

    WASD moves with collision and gravity, Space jumps, Shift sprints, mouse
    looks, F6 toggles a Python Edition LAN host, F7 joins one, Escape closes.
    """
    try:
        import glfw
    except ImportError as exc:
        raise RuntimeError("Desktop mode requires glfw and PyOpenGL; install requirements.txt") from exc

    generator = ChunkGeneratorOverworld(int(seed))
    chunks = {(cx, cz): generator.generate_chunk(cx, cz)
              for cz in range(-1, 2) for cx in range(-1, 2)}

    world = World("New World")
    world.seed = int(seed)
    for chunk in chunks.values():
        world.chunk_provider._chunks[chunk.pos] = chunk

    spawn_chunk = chunks[(0, 0)]
    spawn_y = _surface_y(spawn_chunk, 8, 8) + 1
    player = Entity(world, 8.5, float(spawn_y), 8.5)
    world.add_entity(player)
    camera = Camera(position=(8.5, spawn_y + player.eye_height, 8.5), yaw=0.0, pitch=0.0)
    input_state = InputState()
    lan_server = None
    lan_client = None
    jump_requested = False

    mesh_builder = ChunkMeshBuilder()
    meshes = {}
    for (cx, cz), chunk in chunks.items():
        neighbors = {(cx + dx, cz + dz): chunks[(cx + dx, cz + dz)]
                     for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if (cx + dx, cz + dz) in chunks}
        meshes[(cx, cz)] = mesh_builder.build(chunk, neighbors=neighbors)

    with OpenGLRenderer(1280, 720) as renderer:
        window = renderer.window
        glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        def on_key(_window, key, _scancode, action, _mods):
            nonlocal lan_server, lan_client, jump_requested
            if action == glfw.PRESS:
                input_state.key_down(key)
                if key == glfw.KEY_SPACE:
                    jump_requested = True
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
        for key, mesh in meshes.items():
            renderer.upload_chunk_mesh(key, mesh)

        previous = time.perf_counter()
        tick_accumulator = 0.0
        tick_duration = 1.0 / TICK_RATE
        network_send_timer = 0.0
        try:
            while not renderer.should_close():
                now = time.perf_counter()
                frame_dt = min(now - previous, 0.1)
                previous = now
                camera.rotate(-input_state.mouse_dx * 0.12, input_state.mouse_dy * 0.12)

                forward = camera.forward.copy()
                forward[1] = 0.0
                forward_length = float(np.linalg.norm(forward))
                if forward_length:
                    forward /= forward_length
                right = camera.right.copy()
                right[1] = 0.0
                right_length = float(np.linalg.norm(right))
                if right_length:
                    right /= right_length

                move_x = (float(input_state.is_key_down(glfw.KEY_D))
                          - float(input_state.is_key_down(glfw.KEY_A)))
                move_z = (float(input_state.is_key_down(glfw.KEY_W))
                          - float(input_state.is_key_down(glfw.KEY_S)))
                move_length = math.hypot(move_x, move_z)
                if move_length:
                    move_x /= move_length
                    move_z /= move_length
                speed = PLAYER_SPRINT_SPEED if input_state.is_key_down(glfw.KEY_LEFT_SHIFT) else PLAYER_WALK_SPEED
                horizontal = (right * move_x + forward * move_z) * (speed / TICK_RATE)

                tick_accumulator += frame_dt
                while tick_accumulator >= tick_duration:
                    if jump_requested and player.on_ground:
                        player.motion = Vec3d(player.motion.x, PLAYER_JUMP_VELOCITY, player.motion.z)
                        player.on_ground = False
                    jump_requested = False
                    player.motion = Vec3d(float(horizontal[0]), player.motion.y, float(horizontal[2]))
                    player.on_update()
                    tick_accumulator -= tick_duration

                camera.position = np.asarray(
                    (player.pos.x, player.pos.y + player.eye_height, player.pos.z),
                    dtype=np.float64,
                )

                if lan_client is not None:
                    for message in lan_client.poll():
                        if message.get("type") in ("chat", "player_joined", "player_left", "disconnect"):
                            print(f"[LAN] {message}")
                    network_send_timer += frame_dt
                    if network_send_timer >= 0.1:
                        network_send_timer = 0.0
                        try:
                            lan_client.send_player_state(*camera.position.tolist())
                        except Exception as exc:
                            print(f"[LAN] Connection lost: {exc}")
                            lan_client.close()
                            lan_client = None

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
