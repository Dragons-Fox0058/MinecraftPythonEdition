"""Source-backed vanilla 1.12.2 tool rules for the registered block catalogue."""
from __future__ import annotations
from collections.abc import Mapping
from engine.blocks.material import Material
from engine.blocks.registry import GLOBAL as BLOCK_REGISTRY
from engine.gameplay.items import Item
from engine.gameplay.tools import ToolDefinition, ToolMaterial, ToolRegistry

VANILLA_TOOL_MATERIALS = {
    "wooden": ToolMaterial("wood", 59, 2.0, 0, 15, 0.0),
    "stone": ToolMaterial("stone", 131, 4.0, 1, 5, 1.0),
    "iron": ToolMaterial("iron", 250, 6.0, 2, 14, 2.0),
    "diamond": ToolMaterial("diamond", 1561, 8.0, 3, 10, 3.0),
    "golden": ToolMaterial("gold", 32, 12.0, 0, 22, 0.0),
}

_PICKAXE_EFFECTIVE = frozenset({
    "activator_rail", "coal_ore", "cobblestone", "detector_rail",
    "diamond_block", "diamond_ore", "double_stone_slab", "golden_rail",
    "gold_block", "gold_ore", "ice", "iron_block", "iron_ore", "lapis_block",
    "lapis_ore", "lit_redstone_ore", "mossy_cobblestone", "netherrack",
    "packed_ice", "rail", "red_sandstone", "redstone_ore", "sandstone",
    "stone", "stone_slab", "stone_button", "stone_pressure_plate",
})
_AXE_EFFECTIVE = frozenset({
    "planks", "bookshelf", "log", "log2", "chest", "pumpkin",
    "lit_pumpkin", "melon_block", "ladder", "wooden_button",
    "wooden_pressure_plate",
})
_SHOVEL_EFFECTIVE = frozenset({
    "clay", "dirt", "farmland", "grass", "gravel", "mycelium",
    "sand", "snow", "snow_layer", "soul_sand", "grass_path",
})

def create_vanilla_tool_registry(items: Mapping[str, Item]) -> ToolRegistry:
    """Build rules for supplied items; item IDs are never guessed here.

    Keys use names such as wooden_pickaxe, iron_axe, and diamond_shovel.
    Missing tools remain unavailable; unknown keys and invalid items fail.
    """
    if not isinstance(items, Mapping):
        raise TypeError("items must be a mapping of canonical names to Item")
    valid_keys = {f"{material}_{kind}" for material in VANILLA_TOOL_MATERIALS
                  for kind in ("pickaxe", "axe", "shovel")}
    unknown = set(items) - valid_keys
    if unknown:
        raise ValueError(f"unknown vanilla tool names: {sorted(unknown)!r}")
    registry = ToolRegistry()
    for key, item in items.items():
        if not isinstance(item, Item):
            raise TypeError(f"{key} must map to an Item")
        material_name, tool_class = key.split("_", 1)
        material = VANILLA_TOOL_MATERIALS[material_name]
        if tool_class == "pickaxe":
            effective = {b.registry_name for b in BLOCK_REGISTRY
                         if b.material in (Material.ROCK, Material.IRON, Material.ANVIL)} | set(_PICKAXE_EFFECTIVE)
        elif tool_class == "axe":
            effective = {b.registry_name for b in BLOCK_REGISTRY
                         if b.material in (Material.WOOD, Material.PLANT)} | set(_AXE_EFFECTIVE)
        else:
            effective = {b.registry_name for b in BLOCK_REGISTRY
                         if b.material in (Material.GROUND, Material.SAND, Material.SNOW, Material.CLAY)} | set(_SHOVEL_EFFECTIVE)
        registry.register(ToolDefinition(item, tool_class, material, frozenset(effective)))

    tiers = {
        "obsidian": 3,
        "diamond_ore": 2, "diamond_block": 2, "emerald_ore": 2, "emerald_block": 2,
        "gold_ore": 2, "gold_block": 2, "redstone_ore": 2, "lit_redstone_ore": 2,
        "iron_ore": 1, "iron_block": 1, "lapis_ore": 1, "lapis_block": 1,
    }
    for block in BLOCK_REGISTRY:
        if block.material in (Material.ROCK, Material.IRON, Material.ANVIL):
            registry.set_harvest_requirement(block.registry_name, "pickaxe",
                                             tiers.get(block.registry_name, 0))
    for name in ("snow", "snow_layer"):
        if BLOCK_REGISTRY.by_name(name) is not None:
            registry.set_harvest_requirement(name, "shovel", 0)
    return registry

__all__ = ["VANILLA_TOOL_MATERIALS", "create_vanilla_tool_registry"]