"""Gameplay systems for the Minecraft 1.12.2 target."""

from engine.gameplay.items import Item, ItemRegistry, ItemStack, ITEM_REGISTRY
from engine.gameplay.inventory import Inventory
from engine.gameplay.breaking import BlockBreaking, BlockBreakResult
from engine.gameplay.placement import BlockPlacement, PlacementResult
from engine.gameplay.drops import EntityItem, ItemDropManager

__all__ = ["Item", "ItemRegistry", "ItemStack", "ITEM_REGISTRY", "Inventory", "BlockBreaking", "BlockBreakResult", "BlockPlacement", "PlacementResult", "EntityItem", "ItemDropManager"]
