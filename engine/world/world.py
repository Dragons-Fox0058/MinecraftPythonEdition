"""engine.world.world — World aggregates chunks and exposes block access."""
from __future__ import annotations
from typing import List, Optional, Tuple
from engine.core import BlockPos, AxisAlignedBB
from engine.blocks import BLOCK_REGISTRY, BlockState
import engine.blocks.vanilla_blocks as VB
from engine.world.chunk_provider import ChunkProvider
from engine.gameplay.time import GameRules, WorldTime

AIR_ID = 0


class World:
    def __init__(self, name: str = 'world'):
        self.name = name
        self._provider = ChunkProvider()
        self._entities = []
        self.seed = 0
        # Vanilla level.dat SpawnX/SpawnY/SpawnZ; default world spawn.
        self.spawn_point = BlockPos(0, 64, 0)
        self.game_rules = GameRules()
        self.world_time = WorldTime(day_time=6000)  # noon

    @property
    def time_of_day(self) -> int:
        return self.world_time.time_of_day

    @time_of_day.setter
    def time_of_day(self, value: int) -> None:
        self.world_time.set_day_time(value)

    def tick(self) -> None:
        """Advance world time and update a snapshot of loaded entities."""
        self.world_time.tick(self.game_rules.get_bool("doDaylightCycle"))
        for entity in tuple(self._entities):
            if getattr(entity, "dead", False):
                controller = getattr(entity, "gameplay_controller", None)
                if controller is not None:
                    controller.on_death()
                self.remove_entity(entity)
                continue
            update = getattr(entity, "on_update", None)
            if callable(update):
                update()
            controller = getattr(entity, "gameplay_controller", None)
            if controller is not None:
                controller.tick()

    @property
    def chunk_provider(self) -> ChunkProvider:
        return self._provider

    # --- block access ---
    def is_in_world_bounds(self, y: int) -> bool:
        return 0 <= y < 256

    def get_block_state_id(self, pos: BlockPos) -> int:
        if not self.is_in_world_bounds(pos.y):
            return AIR_ID
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        return chunk.get_block_state_id(pos.x & 15, pos.y, pos.z & 15)

    def set_block_state_id(self, pos: BlockPos, state_id: int) -> None:
        if not self.is_in_world_bounds(pos.y):
            return
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        chunk.set_block_state_id(pos.x & 15, pos.y, pos.z & 15, state_id)

    def get_packed_block_state(self, pos: BlockPos) -> int:
        """Return the complete legacy 1.12.2 state word, including metadata."""
        if not self.is_in_world_bounds(pos.y):
            return 0
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        return chunk.get_packed_block_state(pos.x & 15, pos.y, pos.z & 15)

    def set_packed_block_state(self, pos: BlockPos, packed_state: int) -> None:
        """Set a packed (block_id << 4) | metadata value."""
        if not self.is_in_world_bounds(pos.y):
            return
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        chunk.set_packed_block_state(pos.x & 15, pos.y, pos.z & 15, packed_state)

    def get_block_state(self, pos: BlockPos) -> BlockState:
        sid = self.get_block_state_id(pos)
        # For now: state_id == block_id; actual property encoding comes in phase 3.5.
        block = BLOCK_REGISTRY.by_id(sid)
        if block is None:
            return VB.AIR.default_state
        return block.default_state

    def set_block_state(self, pos: BlockPos, state: BlockState) -> None:
        # Encode state -> id for now as block_id only.
        self.set_block_state_id(pos, state.block.block_id)

    def is_air(self, pos: BlockPos) -> bool:
        return self.get_block_state_id(pos) == AIR_ID

    # --- lighting ---
    def get_sky_light(self, pos: BlockPos) -> int:
        if not self.is_in_world_bounds(pos.y):
            return 15 if pos.y >= 256 else 0
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        return chunk.get_sky_light(pos.x & 15, pos.y, pos.z & 15)

    def get_block_light(self, pos: BlockPos) -> int:
        if not self.is_in_world_bounds(pos.y):
            return 0
        chunk = self._provider.get_or_create(pos.chunk_x, pos.chunk_z)
        return chunk.get_block_light(pos.x & 15, pos.y, pos.z & 15)

    def get_combined_light(self, pos: BlockPos) -> int:
        return max(self.get_sky_light(pos), self.get_block_light(pos))

    # --- collision ---
    def get_collision_boxes(self, aabb: AxisAlignedBB) -> List[AxisAlignedBB]:
        """Return AABBs of all solid blocks intersecting the given box."""
        boxes: List[AxisAlignedBB] = []
        x0 = int(aabb.min_x) - 1
        y0 = max(0, int(aabb.min_y) - 1)
        z0 = int(aabb.min_z) - 1
        x1 = int(aabb.max_x) + 1
        y1 = min(255, int(aabb.max_y) + 1)
        z1 = int(aabb.max_z) + 1
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    pos = BlockPos(x, y, z)
                    state = self.get_block_state(pos)
                    if state.block.can_collide():
                        bb = state.block.get_collision_box(state, pos)
                        if bb is not None and bb.intersects(aabb):
                            boxes.append(bb)
        return boxes

    # --- entities ---
    @property
    def entities(self) -> list:
        return self._entities

    def add_entity(self, entity) -> None:
        self._entities.append(entity)

    def remove_entity(self, entity) -> None:
        if entity in self._entities:
            self._entities.remove(entity)

    def __repr__(self):
        return f'World({self.name!r}, {len(self._provider)} chunks)'
