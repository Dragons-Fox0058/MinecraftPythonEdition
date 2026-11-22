"""engine.blocks.block — Base Block class."""
from __future__ import annotations
from engine.core import AxisAlignedBB

class Block:
    """Base class for all blocks. Subclasses override behaviour."""

    def __init__(self, registry_name: str, block_id: int, material,
                 hardness: float = 1.0, resistance: float = 0.0,
                 light_level: int = 0, opacity: int = 15,
                 is_full_cube: bool = True, is_opaque: bool = True):
        self.registry_name = registry_name
        self.block_id = block_id
        self.material = material
        self.hardness = hardness
        self.resistance = resistance
        self.light_level = light_level
        self.opacity = opacity
        self._is_full_cube = is_full_cube
        self._is_opaque = is_opaque
        self._default_state = None  # set by BlockState intern

    # --- identity ---
    def __repr__(self):
        return f'Block({self.registry_name}#{self.block_id})'

    def __hash__(self): return id(self)

    # --- geometry ---
    def is_full_cube(self) -> bool: return self._is_full_cube

    def is_opaque(self) -> bool:
        # Vanilla rule: a block is an opaque cube iff it is a full cube and
        # its opacity is at least 15 (fully blocks light). Non-full-cube blocks
        # and light-transparent blocks are never opaque cubes.
        if not self._is_full_cube:
            return False
        if self.opacity < 15:
            return False
        return self._is_opaque

    def get_bounding_box(self, state, pos) -> AxisAlignedBB:
        from engine.core import AxisAlignedBB
        return AxisAlignedBB.from_block(pos)

    def get_collision_box(self, state, pos) -> AxisAlignedBB | None:
        if not self.material.blocks_movement:
            return None
        return self.get_bounding_box(state, pos)

    # --- behaviour ---
    def is_solid(self): return self.material.is_solid
    def is_liquid(self): return self.material.is_liquid
    def is_replaceable(self): return self.material.is_replaceable
    def can_collide(self): return self.material.blocks_movement and self._is_full_cube

    # --- states ---
    @property
    def default_state(self):
        return self._default_state

    def create_default_state(self):
        from engine.blocks.state import BlockState
        st = BlockState(self, ())
        return st
