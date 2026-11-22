"""Stateful protocol-340 play session and client/server state synchronization."""
from __future__ import annotations

import math
import queue
import struct
import threading
import time

from engine.core import BlockPos, Vec3d
from engine.entities.entity import Entity
from engine.network.entity_packets import (
    decode_spawn_object, decode_spawn_mob, decode_spawn_player,
    decode_spawn_experience_orb, decode_entity_relative_move,
    decode_entity_teleport, decode_entity_velocity, decode_destroy_entities,
)
from engine.network.window_packets import (
    EMPTY_SLOT, decode_window_items, decode_set_slot, decode_open_window,
    decode_close_window, decode_window_property, decode_confirm_transaction,
    serverbound_click_window, serverbound_close_window,
    serverbound_confirm_transaction, WireItemStack,
)
from engine.network.packets import (
    decode_clientbound_chat, decode_clientbound_chunk_data,
    decode_clientbound_join_game, decode_clientbound_keep_alive,
    decode_clientbound_player_position_look, serverbound_chat,
    serverbound_held_item, serverbound_look, serverbound_player,
    serverbound_position, serverbound_position_look,
)
from engine.network.play import (
    CLIENTBOUND, decode_block_change, decode_change_game_state,
    decode_multi_block_change,
    decode_disconnect, decode_player_abilities, decode_plugin_message,
    decode_respawn, decode_time_update, decode_unload_chunk,
    decode_update_health, serverbound_client_settings,
    serverbound_player_abilities, serverbound_plugin_message,
    serverbound_use_entity, serverbound_teleport_confirm,
)


class RemoteNetworkEntity(Entity):
    """Entity whose transform is authoritative on the remote server."""

    def on_update(self):
        self.ticks_existed += 1
        self.prev_pos = self.pos


class PlaySession:
    """Apply supported play packets to local world/player state.

    Unknown packet IDs are forwarded intact through the event callback.
    """

    def __init__(self, connection, *, world=None, player=None, on_event=None,
                 locale: str = "en_US", view_distance: int = 10):
        if not hasattr(connection, "receive") or not hasattr(connection, "send"):
            raise TypeError("connection must provide receive() and send()")
        if on_event is not None and not callable(on_event):
            raise TypeError("on_event must be callable")
        self.connection = connection
        self.world = world
        self.player = player
        self.on_event = on_event
        self.locale = locale
        self.view_distance = view_distance
        self.connected = True
        self.join_game = None
        self.last_chat = None
        self.last_disconnect = None
        self.last_health = None
        self.last_time = None
        self.last_abilities = None
        self.last_teleport = None
        self.last_respawn = None
        self.last_plugin_message = None
        self.last_game_state = None
        self._client_settings_sent = False
        self._sent_position = None
        self._sent_rotation = None
        self._ticks = 0
        self._last_keep_alive_at = time.monotonic()
        self.network_entities = {}
        self.open_windows = {}
        self.window_items = {}
        self.window_properties = {}
        self.cursor_item = EMPTY_SLOT
        # Socket reads happen on a daemon thread; packet application remains on
        # the caller/game thread so World and Entity state are never mutated
        # from the network worker.
        self._incoming_packets = queue.Queue(maxsize=1024)
        self._receiver_thread = None
        self._receiver_stop = threading.Event()
        self._receiver_error = None
        self._receiver_error_lock = threading.Lock()

    def _emit(self, name: str, value):
        if self.on_event is not None:
            self.on_event(name, value)
        return value

    def _send(self, packet):
        packet_id, payload = packet
        self.connection.send(packet_id, payload)

    def _register_remote_entity(self, entity_id: int, x: float, y: float, z: float,
                                *, entity_uuid=None, entity_type=None):
        if self.player is not None and getattr(self.player, "entity_id", None) == entity_id:
            self.network_entities[entity_id] = self.player
            return self.player
        previous = self.network_entities.pop(entity_id, None)
        if previous is not None and self.world is not None:
            self.world.remove_entity(previous)
        if self.world is None:
            return None
        entity = RemoteNetworkEntity(self.world, x, y, z)
        entity.entity_id = entity_id
        entity.entity_uuid = entity_uuid
        entity.network_type = entity_type
        entity.network_controlled = True
        self.network_entities[entity_id] = entity
        self.world.add_entity(entity)
        return entity

    def _remove_remote_entities(self):
        if self.world is not None:
            for entity in tuple(self.network_entities.values()):
                if entity is not self.player:
                    self.world.remove_entity(entity)
        self.network_entities.clear()

    def send_chat(self, message: str) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_chat(message))

    def send_client_settings(self) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_client_settings(
            locale=self.locale, view_distance=self.view_distance
        ))
        self._client_settings_sent = True

    def send_held_item(self, slot: int) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_held_item(slot))

    def send_player_abilities(self, flags: int, flying_speed: float = 0.05,
                              walking_speed: float = 0.1) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_player_abilities(flags, flying_speed, walking_speed))

    def send_plugin_message(self, channel: str, data: bytes) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_plugin_message(channel, data))

    def close_window(self, window_id: int) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_close_window(window_id))

    def click_window(self, window_id: int, slot: int, button: int,
                     action_number: int, mode: int,
                     clicked_item: WireItemStack) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_click_window(
            window_id, slot, button, action_number, mode, clicked_item
        ))

    def use_entity(self, entity_id: int, action: int, *, target=None,
                   hand: int = 0) -> None:
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        self._send(serverbound_use_entity(
            entity_id, action, target=target, hand=hand
        ))

    def send_player_state(self, *, force: bool = False) -> None:
        """Send a movement packet matching the player's changed state."""
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        if self.player is None:
            raise RuntimeError("player state cannot be sent without a player")
        pos = self.player.pos
        position = (float(pos.x), float(pos.y), float(pos.z))
        yaw = float(getattr(self.player, "yaw", 0.0))
        pitch = float(getattr(self.player, "pitch", 0.0))
        on_ground = bool(getattr(self.player, "on_ground", False))
        if not all(math.isfinite(v) for v in (*position, yaw, pitch)):
            raise ValueError("player position and rotation must be finite")
        moved = self._sent_position != position
        rotated = self._sent_rotation != (yaw, pitch)
        if force or (moved and rotated):
            packet = serverbound_position_look(*position, yaw, pitch, on_ground)
        elif moved:
            packet = serverbound_position(*position, on_ground)
        elif rotated:
            packet = serverbound_look(yaw, pitch, on_ground)
        else:
            packet = serverbound_player(on_ground)
        self._send(packet)
        self._sent_position = position
        self._sent_rotation = (yaw, pitch)

    def process_packet(self, packet_id: int, payload: bytes):
        if not self.connected:
            raise RuntimeError("play session is disconnected")

        if packet_id == CLIENTBOUND["keep_alive"]:
            keep_alive_id = decode_clientbound_keep_alive(payload)
            self._last_keep_alive_at = time.monotonic()
            self.connection.send(0x0B, struct.pack(">q", keep_alive_id))
            return self._emit("keep_alive", keep_alive_id)

        if packet_id == CLIENTBOUND["join_game"]:
            self.join_game = decode_clientbound_join_game(payload)
            if self.player is not None:
                self.player.entity_id = self.join_game.entity_id
                self.player.game_mode = self.join_game.game_mode
            if self.world is not None:
                self.world.dimension = self.join_game.dimension
                self.world.difficulty = self.join_game.difficulty
            if not self._client_settings_sent:
                self.send_client_settings()
            return self._emit("join_game", self.join_game)

        if packet_id == CLIENTBOUND["player_position_look"]:
            packet = decode_clientbound_player_position_look(payload)
            if packet.flags & ~0x1F:
                from engine.network.codec import ProtocolError
                raise ProtocolError("server sent unknown relative teleport flags")
            self.last_teleport = packet
            if self.player is not None:
                current = self.player.pos
                x = packet.x + (current.x if packet.flags & 0x01 else 0.0)
                y = packet.y + (current.y if packet.flags & 0x02 else 0.0)
                z = packet.z + (current.z if packet.flags & 0x04 else 0.0)
                yaw = packet.yaw + (getattr(self.player, "yaw", 0.0)
                                    if packet.flags & 0x08 else 0.0)
                pitch = packet.pitch + (getattr(self.player, "pitch", 0.0)
                                        if packet.flags & 0x10 else 0.0)
                self.player.set_position(x, y, z)
                if hasattr(self.player, "yaw"):
                    self.player.yaw = yaw
                if hasattr(self.player, "pitch"):
                    self.player.pitch = max(-90.0, min(90.0, pitch))
                self._sent_position = (float(x), float(y), float(z))
                self._sent_rotation = (float(yaw), float(pitch))
            self._send(serverbound_teleport_confirm(packet.teleport_id))
            return self._emit("teleport", packet)

        if packet_id == CLIENTBOUND["block_change"]:
            change = decode_block_change(payload)
            if self.world is not None:
                self.world.set_block_state_id(
                    BlockPos(change.x, change.y, change.z), change.state_id
                )
            return self._emit("block_change", change)

        if packet_id == CLIENTBOUND["multi_block_change"]:
            change = decode_multi_block_change(payload)
            if self.world is not None:
                for record in change.records:
                    self.world.set_block_state_id(
                        BlockPos(record.x, record.y, record.z), record.state_id
                    )
            return self._emit("multi_block_change", change)

        if packet_id == CLIENTBOUND["unload_chunk"]:
            chunk = decode_unload_chunk(payload)
            if self.world is not None:
                self.world.chunk_provider.unload(chunk.chunk_x, chunk.chunk_z)
            return self._emit("unload_chunk", chunk)

        if packet_id == CLIENTBOUND["chat"]:
            self.last_chat = decode_clientbound_chat(payload)
            return self._emit("chat", self.last_chat)

        if packet_id == CLIENTBOUND["disconnect"]:
            self.last_disconnect = decode_disconnect(payload)
            self.close()
            return self._emit("disconnect", self.last_disconnect)

        if packet_id == CLIENTBOUND["update_health"]:
            self.last_health = decode_update_health(payload)
            if self.player is not None:
                if hasattr(self.player, "health"):
                    self.player.health = self.last_health.health
                hunger = getattr(self.player, "hunger", None)
                if hunger is None:
                    controller = getattr(self.player, "gameplay_controller", None)
                    hunger = getattr(controller, "hunger", None)
                if hunger is not None:
                    hunger.food_level = max(0, min(20, self.last_health.food))
                    hunger.saturation = max(
                        0.0, min(float(hunger.food_level),
                                 self.last_health.food_saturation)
                    )
            return self._emit("health", self.last_health)

        if packet_id == CLIENTBOUND["time_update"]:
            self.last_time = decode_time_update(payload)
            if self.world is not None:
                self.world.world_time.total_time = max(0, self.last_time.world_age)
                self.world.world_time.day_time = abs(self.last_time.time_of_day)
            return self._emit("time", self.last_time)

        if packet_id == CLIENTBOUND["player_abilities"]:
            self.last_abilities = decode_player_abilities(payload)
            if self.player is not None:
                self.player.invulnerable = bool(self.last_abilities.flags & 0x01)
                self.player.is_flying = bool(self.last_abilities.flags & 0x02)
                self.player.can_fly = bool(self.last_abilities.flags & 0x04)
                self.player.creative_mode = bool(self.last_abilities.flags & 0x08)
                self.player.flying_speed = self.last_abilities.flying_speed
                self.player.field_of_view_modifier = self.last_abilities.fov_modifier
            return self._emit("abilities", self.last_abilities)

        if packet_id == CLIENTBOUND["respawn"]:
            self.last_respawn = decode_respawn(payload)
            self._remove_remote_entities()
            if self.world is not None:
                self.world.dimension = self.last_respawn.dimension
                self.world.difficulty = self.last_respawn.difficulty
                for loaded in tuple(self.world.chunk_provider.all_chunks()):
                    self.world.chunk_provider.unload(loaded.pos.x, loaded.pos.z)
            if self.player is not None:
                self.player.game_mode = self.last_respawn.game_mode
            return self._emit("respawn", self.last_respawn)

        if packet_id == CLIENTBOUND["open_window"]:
            window = decode_open_window(payload)
            self.open_windows[window.window_id] = window
            self.window_items.setdefault(window.window_id, ())
            return self._emit("open_window", window)

        if packet_id == CLIENTBOUND["close_window"]:
            window_id = decode_close_window(payload)
            self.open_windows.pop(window_id, None)
            self.window_items.pop(window_id, None)
            self.window_properties.pop(window_id, None)
            return self._emit("close_window", window_id)

        if packet_id == CLIENTBOUND["window_items"]:
            window = decode_window_items(payload)
            self.window_items[window.window_id] = window.items
            return self._emit("window_items", window)

        if packet_id == CLIENTBOUND["set_slot"]:
            update = decode_set_slot(payload)
            if update.window_id == -1 and update.slot == -1:
                self.cursor_item = update.item
            else:
                current = list(self.window_items.get(update.window_id, ()))
                if update.slot >= 0:
                    if update.slot >= 4096:
                        from engine.network.codec import ProtocolError
                        raise ProtocolError("window slot index exceeds limit")
                    if len(current) <= update.slot:
                        current.extend([EMPTY_SLOT] * (update.slot + 1 - len(current)))
                    current[update.slot] = update.item
                    self.window_items[update.window_id] = tuple(current)
            return self._emit("set_slot", update)

        if packet_id == CLIENTBOUND["window_property"]:
            prop = decode_window_property(payload)
            self.window_properties[(prop.window_id, prop.property_id)] = prop.value
            return self._emit("window_property", prop)

        if packet_id == CLIENTBOUND["confirm_transaction"]:
            confirmation = decode_confirm_transaction(payload)
            if not confirmation.accepted:
                self._send(serverbound_confirm_transaction(
                    confirmation.window_id, confirmation.action_number, False
                ))
            return self._emit("confirm_transaction", confirmation)

        if packet_id == CLIENTBOUND["plugin_message"]:
            self.last_plugin_message = decode_plugin_message(payload)
            return self._emit("plugin_message", self.last_plugin_message)

        if packet_id == CLIENTBOUND["change_game_state"]:
            self.last_game_state = decode_change_game_state(payload)
            return self._emit("game_state", self.last_game_state)

        if packet_id == CLIENTBOUND["spawn_object"]:
            spawn = decode_spawn_object(payload)
            entity = self._register_remote_entity(
                spawn.entity_id, spawn.x, spawn.y, spawn.z,
                entity_uuid=spawn.entity_uuid, entity_type=spawn.object_type
            )
            if entity is not None:
                entity.pitch, entity.yaw = spawn.pitch, spawn.yaw
                entity.motion = Vec3d(*spawn.velocity)
                entity.object_data = spawn.data
            return self._emit("spawn_object", spawn)

        if packet_id == CLIENTBOUND["spawn_mob"]:
            spawn = decode_spawn_mob(payload)
            entity = self._register_remote_entity(
                spawn.entity_id, spawn.x, spawn.y, spawn.z,
                entity_uuid=spawn.entity_uuid, entity_type=spawn.mob_type
            )
            if entity is not None:
                entity.yaw, entity.pitch = spawn.yaw, spawn.pitch
                entity.head_yaw = spawn.head_yaw
                entity.motion = Vec3d(*spawn.velocity)
                entity.metadata_payload = spawn.metadata
            return self._emit("spawn_mob", spawn)

        if packet_id == CLIENTBOUND["spawn_player"]:
            spawn = decode_spawn_player(payload)
            entity = self._register_remote_entity(
                spawn.entity_id, spawn.x, spawn.y, spawn.z,
                entity_uuid=spawn.player_uuid, entity_type="player"
            )
            if entity is not None:
                entity.yaw, entity.pitch = spawn.yaw, spawn.pitch
                entity.metadata_payload = spawn.metadata
            return self._emit("spawn_player", spawn)

        if packet_id == CLIENTBOUND["spawn_experience_orb"]:
            spawn = decode_spawn_experience_orb(payload)
            entity = self._register_remote_entity(
                spawn.entity_id, spawn.x, spawn.y, spawn.z,
                entity_type="experience_orb"
            )
            if entity is not None:
                entity.experience_value = spawn.experience
            return self._emit("spawn_experience_orb", spawn)

        if packet_id in (
            CLIENTBOUND["entity_relative_move"],
            CLIENTBOUND["entity_look_and_relative_move"],
            CLIENTBOUND["entity_look"],
        ):
            move = decode_entity_relative_move(
                payload,
                with_look=packet_id == CLIENTBOUND["entity_look_and_relative_move"],
                look_only=packet_id == CLIENTBOUND["entity_look"],
            )
            entity = self.network_entities.get(move.entity_id)
            if entity is not None:
                entity.set_position(
                    entity.pos.x + move.dx,
                    entity.pos.y + move.dy,
                    entity.pos.z + move.dz,
                )
                if move.yaw is not None:
                    entity.yaw = move.yaw
                    entity.pitch = move.pitch
                entity.on_ground = move.on_ground
            return self._emit("entity_move", move)

        if packet_id == CLIENTBOUND["entity_teleport"]:
            teleport = decode_entity_teleport(payload)
            entity = self.network_entities.get(teleport.entity_id)
            if entity is not None:
                entity.set_position(teleport.x, teleport.y, teleport.z)
                entity.yaw, entity.pitch = teleport.yaw, teleport.pitch
                entity.on_ground = teleport.on_ground
            return self._emit("entity_teleport", teleport)

        if packet_id == CLIENTBOUND["entity_velocity"]:
            velocity = decode_entity_velocity(payload)
            entity = self.network_entities.get(velocity.entity_id)
            if entity is not None:
                entity.motion = Vec3d(velocity.x, velocity.y, velocity.z)
            return self._emit("entity_velocity", velocity)

        if packet_id == CLIENTBOUND["destroy_entities"]:
            destroyed = decode_destroy_entities(payload)
            for entity_id in destroyed.entity_ids:
                entity = self.network_entities.pop(entity_id, None)
                if entity is not None and entity is not self.player and self.world is not None:
                    self.world.remove_entity(entity)
            return self._emit("destroy_entities", destroyed)

        if packet_id == CLIENTBOUND["chunk_data"]:
            has_sky_light = self.world is None or getattr(self.world, "dimension", 0) == 0
            chunk_packet = decode_clientbound_chunk_data(
                payload, has_sky_light=has_sky_light
            )
            if self.world is not None:
                provider = self.world.chunk_provider
                if chunk_packet.ground_up:
                    chunk = provider.get_or_create(
                        chunk_packet.chunk_x, chunk_packet.chunk_z
                    )
                    chunk.blocks.fill(0)
                    chunk.light.fill(0)
                    chunk.biomes.fill(0)
                    if chunk_packet.biomes is not None:
                        for z in range(16):
                            for x in range(16):
                                chunk.biomes[x, z] = chunk_packet.biomes[z * 16 + x]
                else:
                    chunk = provider.get_chunk(
                        chunk_packet.chunk_x, chunk_packet.chunk_z
                    )
                if chunk is not None:
                    for section in chunk_packet.sections:
                        base_y = section.section_y * 16
                        for index, state_id in enumerate(section.block_states):
                            x = index & 15
                            z = (index >> 4) & 15
                            y = base_y + (index >> 8)
                            block_light = (
                                section.block_light[index >> 1]
                                >> (4 if index & 1 else 0)
                            ) & 0x0F
                            sky_light = 0
                            if section.sky_light:
                                sky_light = (
                                    section.sky_light[index >> 1]
                                    >> (4 if index & 1 else 0)
                                ) & 0x0F
                            chunk.blocks[x, z, y] = state_id
                            chunk.light[x, z, y] = (sky_light << 4) | block_light
                    chunk._dirty = True
            return self._emit("chunk_data", chunk_packet)

        return self._emit("unknown_packet", (packet_id, bytes(payload)))

    def check_keep_alive_timeout(self, *, now: float | None = None,
                                 timeout_seconds: float = 20.0) -> bool:
        if not self.connected:
            return False
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        current = time.monotonic() if now is None else float(now)
        if not math.isfinite(current):
            raise ValueError("now must be finite")
        if current - self._last_keep_alive_at > timeout_seconds:
            self.close()
            return False
        return True

    def tick(self) -> bool:
        """Advance one client tick and emit movement at least once per second."""
        if not self.check_keep_alive_timeout():
            return False
        self._ticks += 1
        if self.player is not None:
            pos = self.player.pos
            position = (float(pos.x), float(pos.y), float(pos.z))
            rotation = (float(getattr(self.player, "yaw", 0.0)),
                        float(getattr(self.player, "pitch", 0.0)))
            if (position != self._sent_position or rotation != self._sent_rotation
                    or self._ticks % 20 == 0):
                self.send_player_state()
        return True

    @property
    def receiver_running(self) -> bool:
        return self._receiver_thread is not None and self._receiver_thread.is_alive()

    def start_receiver(self) -> None:
        """Start background socket reads without applying world changes off-thread."""
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        if self.receiver_running:
            return
        if self._receiver_thread is not None:
            raise RuntimeError("network receiver has already stopped")
        self._receiver_stop.clear()
        self._receiver_thread = threading.Thread(
            target=self._receive_loop,
            name="MinecraftNetworkReceiver",
            daemon=True,
        )
        self._receiver_thread.start()

    def _receive_loop(self) -> None:
        while not self._receiver_stop.is_set():
            try:
                packet = self.connection.receive()
            except Exception as exc:
                if not self._receiver_stop.is_set():
                    with self._receiver_error_lock:
                        self._receiver_error = exc
                return
            while not self._receiver_stop.is_set():
                try:
                    self._incoming_packets.put(packet, timeout=0.1)
                    break
                except queue.Full:
                    # Back-pressure: stop reading the socket until the game
                    # thread has drained queued packets. Never silently drop.
                    continue

    def poll_received(self, *, max_packets: int = 100) -> int:
        """Apply up to max_packets queued packets on the calling thread."""
        if not self.connected:
            return 0
        if isinstance(max_packets, bool) or not isinstance(max_packets, int) or max_packets < 1:
            raise ValueError("max_packets must be a positive integer")
        if self._receiver_thread is None:
            raise RuntimeError("network receiver has not been started")
        processed = 0
        while processed < max_packets:
            try:
                packet_id, payload = self._incoming_packets.get_nowait()
            except queue.Empty:
                break
            self.process_packet(packet_id, payload)
            processed += 1
            if not self.connected:
                break

        with self._receiver_error_lock:
            receiver_error = self._receiver_error
        if receiver_error is not None and self._incoming_packets.empty():
            self.close()
            raise ConnectionError("Minecraft network receiver stopped") from receiver_error
        return processed

    def process_next(self, *, timeout: float = 20.0):
        if not self.connected:
            raise RuntimeError("play session is disconnected")
        if self.receiver_running:
            raise RuntimeError("process_next cannot be used while the background receiver is running")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        if hasattr(self.connection, "set_timeout"):
            self.connection.set_timeout(timeout)
        try:
            packet_id, payload = self.connection.receive()
        except TimeoutError as exc:
            self.close()
            raise TimeoutError("Minecraft server did not send a packet in time") from exc
        except (OSError, EOFError):
            self.close()
            raise
        finally:
            if hasattr(self.connection, "set_timeout"):
                try:
                    self.connection.set_timeout(None)
                except (OSError, ValueError):
                    pass
        return self.process_packet(packet_id, payload)

    def close(self):
        self._remove_remote_entities()
        was_connected = self.connected
        self.connected = False
        self._receiver_stop.set()
        if was_connected:
            self.connection.close()
        thread = self._receiver_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.5)


__all__ = ["PlaySession"]
