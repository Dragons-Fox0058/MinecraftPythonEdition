"""Desktop single-player survival foundation with Python Edition LAN controls."""
from __future__ import annotations

import math
import random
import time
import uuid
from pathlib import Path

import numpy as np

from engine.core import Vec3d, BlockPos
from engine.entities.entity import Entity
from engine.gameplay.breaking import BlockBreaking
from engine.gameplay.items import Item, ItemStack, ItemRegistry
from engine.gameplay.player import PlayerController
from engine.gameplay.effects import StatusEffectManager
from engine.gameplay.inventory import Inventory
from engine.gameplay.drops import EntityItem
from engine.gameplay.vanilla_tools import create_vanilla_tool_items, create_vanilla_tool_registry
from engine.gameplay.vanilla_drops import resolve_vanilla_block_drops
from engine.gameplay.vanilla_enchantments import get_tool_enchantments
from engine.gameplay.crafting import CraftingGrid
from engine.gameplay.vanilla_recipes import create_vanilla_tool_recipes
from engine.gameplay.interaction import InteractionManager
from engine.input.state import InputState
from engine.network.python_edition import PythonEditionClient
from engine.render.camera import Camera
from engine.render.mesh import ChunkMeshBuilder
from engine.render.opengl import OpenGLRenderer
from engine.server.local import PythonEditionServer, ServerConfig
from engine.world.world import World
from engine.worldgen.generator import ChunkGeneratorOverworld
from engine.persistence.world import load_world, save_world, load_world_player, save_world_player


TICK_RATE = 20.0
PLAYER_WALK_SPEED = 4.3
PLAYER_SPRINT_SPEED = 5.6
PLAYER_JUMP_VELOCITY = 0.42
RENDER_DISTANCE_CHUNKS = 2


class DesktopPlayer(Entity):
    """Living player entity used by the desktop single-player session."""

    def __init__(self, world, x, y, z):
        super().__init__(world, x, y, z)
        self.max_health = 20.0
        self.health = 20.0
        self.status_effects = StatusEffectManager()
        self.yaw = 0.0
        self.pitch = 0.0

    def heal(self, amount):
        if self.dead or amount <= 0:
            return False
        self.health = min(self.max_health, self.health + float(amount))
        return True

    def damage(self, amount):
        if self.dead or amount <= 0:
            return False
        self.health = max(0.0, self.health - float(amount))
        if self.health <= 0:
            self.kill()
        return True


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
        world.spawn_point = BlockPos(8, 0, 8)
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
    world.spawn_point = BlockPos(spawn.x, spawn_y, spawn.z)
    player = DesktopPlayer(world, spawn.x + 0.5, float(spawn_y), spawn.z + 0.5)
    world.add_entity(player)
    camera = Camera(position=(player.pos.x, spawn_y + player.eye_height, player.pos.z), yaw=0.0, pitch=0.0)
    input_state = InputState()
    lan_server = None
    lan_client = None
    jump_requested = False
    inventory = Inventory()
    selected_hotbar_slot = inventory.selected_hotbar_slot
    hotbar_block_ids = (1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 20, 21, 24, 49, 56, 73, 74, 129, 153)
    item_registry = ItemRegistry()
    from engine.blocks import BLOCK_REGISTRY
    block_items = {
        block_id: Item(block_id, BLOCK_REGISTRY.by_id(block_id).registry_name)
        for block_id in hotbar_block_ids if BLOCK_REGISTRY.by_id(block_id) is not None
    }
    for item in block_items.values():
        item_registry.register(item)
    drop_items = dict(block_items)
    flint_item = Item(318, "minecraft:flint")
    ordinary_drop_items = {
        263: Item(263, "minecraft:coal"),
        264: Item(264, "minecraft:diamond"),
        331: Item(331, "minecraft:redstone"),
        351: Item(351, "minecraft:dye", has_subtypes=True),
        388: Item(388, "minecraft:emerald"),
        406: Item(406, "minecraft:quartz"),
        318: flint_item,
    }
    for item in ordinary_drop_items.values():
        item_registry.register(item)
    drop_items.update(ordinary_drop_items)
    item_to_block = {item: block_id for block_id, item in block_items.items()}

    # Register the complete vanilla pickaxe/axe/shovel item subset. A small
    # wooden-tool bootstrap is supplied only to brand-new local test worlds;
    # existing player saves retain their own inventory unchanged.
    tool_items = create_vanilla_tool_items()
    for item in tool_items.values():
        item_registry.register(item)
    tool_registry = create_vanilla_tool_registry(tool_items)
    ingredient_items = {
        "planks": block_items[5],
        "cobblestone": block_items[4],
        "iron_ingot": Item(265, "minecraft:iron_ingot"),
        "diamond": ordinary_drop_items[264],
        "gold_ingot": Item(266, "minecraft:gold_ingot"),
        "stick": Item(280, "minecraft:stick"),
    }
    for item in (ingredient_items["iron_ingot"], ingredient_items["gold_ingot"], ingredient_items["stick"]):
        item_registry.register(item)
    tool_recipes = create_vanilla_tool_recipes(tool_items, ingredient_items)
    crafting_grid = CraftingGrid(3, 3)
    controller = PlayerController(
        player, inventory=inventory, difficulty="normal",
        tool_registry=tool_registry,
    )
    player_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"minecraft-python-edition:{world.name}:{world.seed}")
    player_file = save_directory / "playerdata" / f"{player_uuid}.dat"
    if player_file.is_file():
        load_world_player(save_directory, player_uuid, player, controller, item_registry)
    else:
        inventory.set_slot(0, ItemStack(tool_items["wooden_pickaxe"]))
        inventory.set_slot(1, ItemStack(tool_items["wooden_axe"]))
        inventory.set_slot(2, ItemStack(tool_items["wooden_shovel"]))
    interaction = InteractionManager(world)

    def resolve_block_drop(block, pos):
        # BlockBreaking calls this only after the held tool passes the harvest
        # requirement; this resolver then applies the supported vanilla loot
        # rule. Seed by world and position so saved worlds stay deterministic.
        drop_seed = (
            int(world.seed) ^ (pos.x * 341873128712)
            ^ (pos.y * 132897987541) ^ (pos.z * 42317861)
        )
        fortune, silk_touch = get_tool_enchantments(inventory.selected_item)
        return resolve_vanilla_block_drops(
            block, drop_items, flint_item=flint_item,
            rng=random.Random(drop_seed), fortune=fortune,
            silk_touch=silk_touch,
        )

    block_breaking = BlockBreaking(
        world, drop_resolver=resolve_block_drop, tool_registry=tool_registry,
    )
    mouse_left_down = False
    paused = False
    inventory_open = False
    crafting_open = False

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
            nonlocal lan_server, lan_client, jump_requested, selected_hotbar_slot, paused, inventory_open, crafting_open, mouse_left_down
            if action == glfw.PRESS:
                input_state.key_down(key)
                if key == glfw.KEY_SPACE:
                    jump_requested = True
                if glfw.KEY_1 <= key <= glfw.KEY_9:
                    selected_hotbar_slot = key - glfw.KEY_1
                    inventory.select_hotbar_slot(selected_hotbar_slot)
                    stack = inventory.get_hotbar_slot(selected_hotbar_slot)
                    label = "empty" if stack.is_empty else f"{stack.item.name} x{stack.count}"
                    glfw.set_window_title(window, f"Minecraft Python Edition — Slot {selected_hotbar_slot + 1}: {label}")
                if key == glfw.KEY_Q and paused and not inventory_open:
                    # The pause screen's save-and-quit action; the finally block
                    # persists world and player data before the window exits.
                    glfw.set_window_should_close(window, True)
                if key == glfw.KEY_ESCAPE:
                    if inventory_open:
                        inventory_open = False
                        crafting_open = False
                    else:
                        paused = not paused
                    input_state.set_focus(False)
                    input_state.set_focus(True)
                    input_state.mouse_x = input_state.mouse_y = 0.0
                    input_state.mouse_dx = input_state.mouse_dy = 0.0
                    glfw.set_input_mode(
                        window, glfw.CURSOR,
                        glfw.CURSOR_NORMAL if (paused or inventory_open) else glfw.CURSOR_DISABLED,
                    )
                    title = ("Minecraft Python Edition — CRAFTING" if crafting_open else "Minecraft Python Edition — INVENTORY") if inventory_open else ("Minecraft Python Edition — PAUSED (ESC to resume)" if paused else f"Minecraft Python Edition — {world.name}")
                    glfw.set_window_title(window, title)
                elif key == glfw.KEY_E and not paused:
                    inventory_open = not inventory_open
                    crafting_open = False
                    mouse_left_down = False
                    block_breaking.reset()
                    input_state.set_focus(False)
                    input_state.set_focus(True)
                    input_state.mouse_x = input_state.mouse_y = 0.0
                    input_state.mouse_dx = input_state.mouse_dy = 0.0
                    glfw.set_input_mode(
                        window, glfw.CURSOR,
                        glfw.CURSOR_NORMAL if inventory_open else glfw.CURSOR_DISABLED,
                    )
                    glfw.set_window_title(window, "Minecraft Python Edition — INVENTORY" if inventory_open else f"Minecraft Python Edition — {world.name}")
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
            for tx, tz in ((cx, cz), (cx - 1, cz), (cx + 1, cz), (cx, cz - 1), (cx, cz + 1)):
                key = (tx, tz)
                chunk = chunks.get(key)
                if chunk is None:
                    continue
                neighbors = {(tx + dx, tz + dz): chunks[(tx + dx, tz + dz)]
                             for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
                             if (tx + dx, tz + dz) in chunks}
                renderer.upload_chunk_mesh(key, mesh_builder.build(chunk, neighbors=neighbors))

        def on_mouse_button(_window, button, action, _mods):
            nonlocal mouse_left_down, selected_hotbar_slot
            if inventory_open:
                if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
                    cursor_x, cursor_y = glfw.get_cursor_pos(window)
                    window_w, window_h = glfw.get_window_size(window)
                    if window_w > 0 and window_h > 0:
                        nx = cursor_x * 2.0 / window_w - 1.0
                        ny = 1.0 - cursor_y * 2.0 / window_h
                        if crafting_open:
                            grid_col = math.floor((nx + 0.32) / 0.077)
                            grid_row = math.floor((0.22 - ny) / 0.087)
                            if 0 <= grid_col < 3 and 0 <= grid_row < 3:
                                grid_slot = grid_row * 3 + grid_col
                                inventory.slots[selected_hotbar_slot], crafting_grid.slots[grid_slot] = (
                                    crafting_grid.slots[grid_slot], inventory.slots[selected_hotbar_slot]
                                )
                                return
                            if 0.15 <= nx <= 0.25 and 0.12 <= ny <= 0.22:
                                recipe = crafting_grid.find_recipe(tool_recipes)
                                if recipe is not None and inventory.add_item(recipe.output):
                                    crafting_grid.craft(tool_recipes)
                                return
                            col = math.floor((nx + 0.37) / 0.078)
                            row = math.floor((-0.015 - ny) / 0.08)
                        else:
                            col = math.floor((nx + 0.3915) / 0.087)
                            row = math.floor((0.245 - ny) / 0.13)
                        if 0 <= col < 9 and 0 <= row < 4:
                            slot = row * 9 + col
                            if slot < 9:
                                selected_hotbar_slot = slot
                                inventory.select_hotbar_slot(slot)
                            else:
                                inventory.swap_slots(selected_hotbar_slot, slot)
                return
            if button == glfw.MOUSE_BUTTON_LEFT:
                mouse_left_down = action != glfw.RELEASE
                if action == glfw.RELEASE:
                    block_breaking.reset()
            elif button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
                hit = interaction.ray_trace_blocks(
                    Vec3d(*camera.position.tolist()), Vec3d(*camera.forward.tolist()), 4.5
                )
                if hit is None:
                    return
                hit_block_id = world.get_block_state_id(hit.pos)
                hit_block = BLOCK_REGISTRY.by_id(hit_block_id)
                if hit_block is not None and hit_block.registry_name == "crafting_table":
                    inventory_open = True
                    crafting_open = True
                    mouse_left_down = False
                    block_breaking.reset()
                    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_NORMAL)
                    glfw.set_window_title(window, "Minecraft Python Edition — CRAFTING")
                    return
                if hit.side_hit is None:
                    return
                target = hit.pos.offset(hit.side_hit)
                if (target.chunk_x, target.chunk_z) not in chunks or not world.is_in_world_bounds(target.y):
                    return
                held_stack = inventory.selected_item
                if held_stack.is_empty:
                    return
                block_id = item_to_block.get(held_stack.item)
                if block_id is None:
                    return
                block = BLOCK_REGISTRY.by_id(block_id)
                if block is None or not block.is_full_cube:
                    return
                box = block.get_collision_box(block.default_state, target)
                if box is not None and box.intersects(player.get_entity_bounding_box()):
                    return
                world.set_block_state_id(target, block_id)
                held_stack.shrink(1)
                block_breaking.reset()
                refresh_chunk_mesh(target.chunk_x, target.chunk_z)

        def on_mouse(_window, x, y):
            if input_state.mouse_x == 0.0 and input_state.mouse_y == 0.0:
                input_state.mouse_x, input_state.mouse_y = x, y
                return
            input_state.mouse_move(x, y)

        def on_scroll(_window, _x_offset, y_offset):
            nonlocal selected_hotbar_slot
            if paused or inventory_open or y_offset == 0:
                return
            selected_hotbar_slot = (selected_hotbar_slot - int(math.copysign(1, y_offset))) % 9
            inventory.select_hotbar_slot(selected_hotbar_slot)

        glfw.set_key_callback(window, on_key)
        glfw.set_cursor_pos_callback(window, on_mouse)
        glfw.set_mouse_button_callback(window, on_mouse_button)
        glfw.set_scroll_callback(window, on_scroll)
        for key, mesh in meshes.items():
            renderer.upload_chunk_mesh(key, mesh)

        last_render_center = (center_cx, center_cz)

        def sync_render_distance(center_x, center_z):
            desired = {
                (center_x + dx, center_z + dz)
                for dz in range(-RENDER_DISTANCE_CHUNKS, RENDER_DISTANCE_CHUNKS + 1)
                for dx in range(-RENDER_DISTANCE_CHUNKS, RENDER_DISTANCE_CHUNKS + 1)
            }
            for key in tuple(chunks):
                if key not in desired:
                    renderer.remove_chunk(key)
                    del chunks[key]
            for cx, cz in desired:
                if (cx, cz) not in chunks:
                    chunks[(cx, cz)] = world.chunk_provider.get_or_create(cx, cz)
            for cx, cz in desired:
                chunk = chunks[(cx, cz)]
                neighbors = {(cx + dx, cz + dz): chunks[(cx + dx, cz + dz)]
                             for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
                             if (cx + dx, cz + dz) in chunks}
                renderer.upload_chunk_mesh((cx, cz), mesh_builder.build(chunk, neighbors=neighbors))

        previous = time.perf_counter()
        tick_accumulator = 0.0
        tick_duration = 1.0 / TICK_RATE
        network_send_timer = 0.0
        try:
            while not renderer.should_close():
                now = time.perf_counter()
                frame_dt = min(now - previous, 0.1)
                previous = now
                if not paused and not inventory_open:
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
                if paused or inventory_open:
                    move_x = move_z = move_length = 0.0
                if move_length:
                    move_x /= move_length
                    move_z /= move_length
                speed = PLAYER_SPRINT_SPEED if input_state.is_key_down(glfw.KEY_LEFT_SHIFT) else PLAYER_WALK_SPEED
                horizontal = (right * move_x + forward * move_z) * (speed / TICK_RATE)

                tick_accumulator += frame_dt if not (paused or inventory_open) else 0.0
                while not (paused or inventory_open) and tick_accumulator >= tick_duration:
                    if jump_requested and player.on_ground:
                        player.motion = Vec3d(player.motion.x, PLAYER_JUMP_VELOCITY, player.motion.z)
                        player.on_ground = False
                    jump_requested = False
                    player.motion = Vec3d(float(horizontal[0]), player.motion.y, float(horizontal[2]))
                    player.on_update()
                    if speed == PLAYER_SPRINT_SPEED and move_length > 0:
                        controller.add_exhaustion(0.001)
                    controller.tick()
                    if player.dead:
                        controller.on_death()
                        player.dead = False
                        player.health = player.max_health
                        player.set_position(
                            world.spawn_point.x + 0.5, world.spawn_point.y,
                            world.spawn_point.z + 0.5,
                        )
                        player.motion = Vec3d(0.0, 0.0, 0.0)
                    if mouse_left_down:
                        hit = interaction.ray_trace_blocks(
                            Vec3d(*camera.position.tolist()), Vec3d(*camera.forward.tolist()), 4.5
                        )
                        if hit is None:
                            block_breaking.reset()
                        else:
                            result = block_breaking.damage_block(
                                hit.pos, dig_speed=1.0, can_harvest=False,
                                tool_stack=inventory.selected_item,
                            )
                            if result.broken:
                                refresh_chunk_mesh(hit.pos.chunk_x, hit.pos.chunk_z)
                    for dropped in tuple(world.entities):
                        if isinstance(dropped, EntityItem):
                            dropped.on_update()
                            dx = dropped.pos.x - player.pos.x
                            dy = dropped.pos.y - (player.pos.y + 0.8)
                            dz = dropped.pos.z - player.pos.z
                            if dx * dx + dy * dy + dz * dz <= 1.44:
                                dropped.try_pickup(inventory)
                    tick_accumulator -= tick_duration

                camera.position = np.asarray(
                    (player.pos.x, player.pos.y + player.eye_height, player.pos.z),
                    dtype=np.float64,
                )
                current_render_center = (math.floor(player.pos.x) >> 4, math.floor(player.pos.z) >> 4)
                if current_render_center != last_render_center:
                    sync_render_distance(*current_render_center)
                    last_render_center = current_render_center

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
                    renderer.render(
                        camera.view_projection_matrix(width / height),
                        hud_state={
                            "selected_slot": selected_hotbar_slot,
                            "health": player.health,
                            "food": controller.hunger.food_level,
                            "paused": paused or inventory_open,
                            "inventory_slots": [(0, 0) if stack.is_empty else (stack.item.item_id, stack.count) for stack in inventory.slots] if inventory_open else None,
                            "crafting_slots": [(0, 0) if stack.is_empty else (stack.item.item_id, stack.count) for stack in crafting_grid.slots] if crafting_open else None,
                            "crafting_open": crafting_open,
                            "crafting_result": (0, 0) if crafting_grid.find_recipe(tool_recipes) is None else (crafting_grid.find_recipe(tool_recipes).output.item.item_id, crafting_grid.find_recipe(tool_recipes).output.count),
                        },
                    )
        finally:
            world.spawn_point = BlockPos(
                math.floor(player.pos.x), math.floor(player.pos.y), math.floor(player.pos.z)
            )
            save_world(world, save_directory)
            save_world_player(save_directory, player, controller, item_registry, player_uuid=player_uuid)
            if lan_client is not None:
                lan_client.close()
            if lan_server is not None:
                lan_server.stop()


if __name__ == "__main__":
    main()
