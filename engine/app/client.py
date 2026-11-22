"""Desktop single-player survival foundation with Python Edition LAN controls."""
from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np

from engine.core import Vec3d, BlockPos, EnumFacing
from engine.entities.entity import Entity
from engine.gameplay.breaking import BlockBreaking
from engine.gameplay.interaction import InteractionManager
from engine.input.state import InputState
from engine.network.python_edition import PythonEditionClient
from engine.render.camera import Camera
from engine.render.mesh import ChunkMeshBuilder
from engine.render.opengl import OpenGLRenderer
from engine.server.local import PythonEditionServer, ServerConfig
from engine.world.world import World
from engine.worldgen.generator import ChunkGeneratorOverworld
from engine.persistence.world import load_world, save_world


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


def main(*, seed: int = 0, world_name: str = "New World", save_path: str | None = None) -> None:
    """Open the desktop world.

    WASD moves with collision and gravity, Space jumps, Shift sprints, mouse
    looks, F6 toggles a Python Edition LAN host, F7 joins one, Escape closes.
    """
    try:
        import glfw
    except ImportError as exc:
        raise RuntimeError("Desktop mode requires glfw and PyOpenGL; install requirements.txt") from exc

    save_directory = Path(save_path) if save_path else Path("saves") / world_name
    if (save_directory / "level.dat").is_file():
        world = load_world(save_directory)
        seed = world.seed
    else:
        world = World(world_name)
        world.seed = int(seed)
        world._provider = __import__(
            "engine.worldgen.provider", fromlist=["ChunkProviderOverworld"]
        ).ChunkProviderOverworld(world.seed)

    spawn = world.spawn_point
    center_cx, center_cz = spawn.x >> 4, spawn.z >> 4
    chunks = {}
    for cz in range(center_cz - 1, center_cz + 2):
        for cx in range(center_cx - 1, center_cx + 2):
            chunks[(cx, cz)] = world.chunk_provider.get_or_create(cx, cz)

    spawn_chunk = chunks[(center_cx, center_cz)]
    local_x, local_z = spawn.x & 15, spawn.z & 15
    if spawn.y <= 0 or spawn.y >= 255:
        spawn_y = _surface_y(spawn_chunk, local_x, local_z) + 1
    else:
        spawn_y = spawn.y
    player = Entity(world, spawn.x + 0.5, float(spawn_y), spawn.z + 0.5)
    world.add_entity(player)
    camera = Camera(position=(8.5, spawn_y + player.eye_height, 8.5), yaw=0.0, pitch=0.0)
    input_state = InputState()
    lan_server = None
    lan_client = None
    jump_requested = False
    selected_hotbar_slot = 0
    hotbar_block_ids = (1, 3, 4, 5, 12, 13, 20, 24, 49)
    interaction = InteractionManager(world)
    block_breaking = BlockBreaking(world)
    mouse_left_down = False

    mesh_builder = ChunkMeshBuilder()
    meshes = {}
    for (cx, cz), chunk in chunks.items():
        neighbors = {(cx + dx, cz + dz): chunks[(cx + dx, cz + dz)]
                     for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if (cx + dx, cz + dz) in chunks}
        meshes[(cx, cz)] = mesh_builder.build(chunk, neighbors=neighbors)

    with OpenGLRenderer(1280, 720, title=f"Minecraft Python Edition — {world.name}") as renderer:
        window = renderer.window
        glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        def on_key(_window, key, _scancode, action, _mods):
            nonlocal lan_server, lan_client, jump_requested, selected_hotbar_slot
            if action == glfw.PRESS:
                input_state.key_down(key)
                if key == glfw.KEY_SPACE:
                    jump_requested = True
                if glfw.KEY_1 <= key <= glfw.KEY_9:
                    selected_hotbar_slot = key - glfw.KEY_1
                    glfw.set_window_title(window, f"Minecraft Python Edition — Slot {selected_hotbar_slot + 1}")
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


        def refresh_chunk_mesh(cx, cz):
            key = (cx, cz)
            chunk = chunks.get(key)
            if chunk is None:
                return
            neighbors = {(cx + dx, cz + dz): chunks[(cx + dx, cz + dz)]
                         for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
                         if (cx + dx, cz + dz) in chunks}
            renderer.upload_chunk_mesh(key, mesh_builder.build(chunk, neighbors=neighbors))

        def on_mouse_button(_window, button, action, _mods):
            nonlocal mouse_left_down
            if button == glfw.MOUSE_BUTTON_LEFT:
                mouse_left_down = action != glfw.RELEASE
                if action == glfw.RELEASE:
                    block_breaking.reset()
            elif button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
                hit = interaction.ray_trace_blocks(
                    Vec3d(*camera.position.tolist()), Vec3d(*camera.forward.tolist()), 5.0
                )
                if hit is None or hit.side_hit is None:
                    return
                target = hit.pos.offset(hit.side_hit)
                if (target.chunk_x, target.chunk_z) not in chunks or not world.is_in_world_bounds(target.y):
                    return
                block_id = hotbar_block_ids[selected_hotbar_slot]
                from engine.blocks import BLOCK_REGISTRY
                block = BLOCK_REGISTRY.by_id(block_id)
                if block is None or not block.is_full_cube:
                    return
                box = block.get_collision_box(block.default_state, target)
                if box is not None and box.intersects(player.get_entity_bounding_box()):
                    return
                world.set_block_state_id(target, block_id)
                block_breaking.reset()
                refresh_chunk_mesh(target.chunk_x, target.chunk_z)

        def on_mouse(_window, x, y):
            if input_state.mouse_x == 0.0 and input_state.mouse_y == 0.0:
                input_state.mouse_x, input_state.mouse_y = x, y
                return
            input_state.mouse_move(x, y)

        glfw.set_key_callback(window, on_key)
        glfw.set_cursor_pos_callback(window, on_mouse)
        glfw.set_mouse_button_callback(window, on_mouse_button)
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

                if mouse_left_down:
                    hit = interaction.ray_trace_blocks(
                        Vec3d(*camera.position.tolist()), Vec3d(*camera.forward.tolist()), 5.0
                    )
                    if hit is None:
                        block_breaking.reset()
                    else:
                        result = block_breaking.damage_block(hit.pos, dig_speed=1.0, can_harvest=True)
                        if result.broken:
                            refresh_chunk_mesh(hit.pos.chunk_x, hit.pos.chunk_z)

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
            world.spawn_point = BlockPos(
                math.floor(player.pos.x), math.floor(player.pos.y), math.floor(player.pos.z)
            )
            save_world(world, save_directory)
            if lan_client is not None:
                lan_client.close()
            if lan_server is not None:
                lan_server.stop()


if __name__ == "__main__":
    main()
