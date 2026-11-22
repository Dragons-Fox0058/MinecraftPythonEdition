"""engine.blocks.material — Material types from 1.12.2."""
from __future__ import annotations
from enum import Enum

class Material(Enum):
    AIR       = ('air',       False, False, False, False)
    GRASS     = ('grass',     True,  True,  True,  False)
    GROUND    = ('ground',    True,  True,  True,  False)
    WOOD      = ('wood',      True,  True,  True,  False)
    ROCK      = ('rock',      True,  True,  True,  False)
    IRON      = ('iron',      True,  True,  True,  False)
    ANVIL     = ('anvil',     True,  True,  True,  False)
    WATER     = ('water',     False, False, False, True)
    LAVA      = ('lava',      False, False, False, True)
    LEAVES    = ('leaves',    True,  True,  False, False)
    PLANT     = ('plant',     False, False, False, False)
    SAND      = ('sand',      True,  True,  True,  False)
    SNOW      = ('snow',      True,  True,  True,  False)
    FIRE      = ('fire',      False, False, False, False)
    GLASS     = ('glass',     True,  False, False, False)
    CLOTH     = ('cloth',     True,  True,  True,  False)
    TNT       = ('tnt',       True,  True,  False, False)
    CACTUS    = ('cactus',    True,  True,  False, False)
    CLAY      = ('clay',      True,  True,  True,  False)
    GOURD     = ('gourd',     True,  True,  True,  False)
    DRAGON_EGG= ('dragon_egg',True,  True,  False, False)
    PORTAL    = ('portal',    False, False, False, False)
    CAKE      = ('cake',      True,  True,  False, False)
    WEB       = ('web',       True,  True,  False, False)
    PISTON    = ('piston',    True,  True,  False, False)
    CIRCUIT   = ('circuit',   True,  False, False, False)

    def __init__(self, name, solid, blocks_light, blocks_movement, is_liquid):
        self.material_name = name
        self.is_solid = solid
        self.blocks_light = blocks_light
        self.blocks_movement = blocks_movement
        self.is_liquid = is_liquid

    @property
    def is_opaque(self): return self.blocks_light

    @property
    def is_replaceable(self):
        return self in (Material.AIR, Material.PLANT, Material.WATER, Material.LAVA, Material.FIRE)

    def __repr__(self):
        return f'Material.{self.name}'
