"""engine.blocks.state — Immutable interned BlockState."""
from __future__ import annotations

class BlockState:
    """Immutable snapshot of (Block, properties). Interned per Block."""
    __slots__ = ('_block', '_props', '_interned')

    def __init__(self, block, properties: tuple):
        self._block = block
        # properties: tuple of (name, value) sorted by name for canonical form
        self._props = tuple(sorted(properties, key=lambda kv: kv[0]))
        self._interned = False

    @property
    def block(self): return self._block

    @property
    def properties(self): return self._props

    def get(self, name, default=None):
        for k, v in self._props:
            if k == name: return v
        return default

    def with_property(self, name, value):
        if self.get(name) == value:
            return self
        new_props = tuple((k, value if k == name else v) for k, v in self._props if k != name)
        new_props = tuple(sorted(new_props + ((name, value),), key=lambda kv: kv[0]))
        return BlockState(self._block, new_props)

    def __eq__(self, o):
        return isinstance(o, BlockState) and self._block is o._block and self._props == o._props

    def __hash__(self):
        return hash((id(self._block), self._props))

    def __repr__(self):
        if not self._props:
            return f'BlockState({self._block.registry_name})'
        p = ', '.join(f'{k}={v}' for k, v in self._props)
        return f'BlockState({self._block.registry_name}, {p})'
