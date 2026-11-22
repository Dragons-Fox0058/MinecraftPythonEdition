"""engine.blocks.registry — Global BlockRegistry (numeric ID <-> Block)."""
from __future__ import annotations
from typing import Dict, Optional
from engine.blocks.block import Block

class BlockRegistry:
    def __init__(self):
        self._by_id: Dict[int, Block] = {}
        self._by_name: Dict[str, Block] = {}
        self._frozen = False

    def register(self, block: Block) -> Block:
        if self._frozen:
            raise RuntimeError('Registry is frozen')
        if block.block_id in self._by_id:
            raise ValueError(f'block_id {block.block_id} already registered')
        if block.registry_name in self._by_name:
            raise ValueError(f'registry_name {block.registry_name!r} already registered')
        self._by_id[block.block_id] = block
        self._by_name[block.registry_name] = block
        block._default_state = block.create_default_state()
        return block

    def freeze(self): self._frozen = True

    def by_id(self, n: int) -> Optional[Block]: return self._by_id.get(n)
    def by_name(self, s: str) -> Optional[Block]: return self._by_name.get(s)
    def require_id(self, n: int) -> Block:
        b = self.by_id(n)
        if b is None: raise KeyError(f'unknown block_id {n}')
        return b
    def require_name(self, s: str) -> Block:
        b = self.by_name(s)
        if b is None: raise KeyError(f'unknown registry_name {s!r}')
        return b

    def __len__(self): return len(self._by_id)
    def __iter__(self): return iter(self._by_id.values())

# Global registry instance
GLOBAL = BlockRegistry()
