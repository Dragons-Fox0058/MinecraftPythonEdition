"""Gameplay systems for the Minecraft 1.12.2 target."""

from engine.gameplay.items import Item, ItemRegistry, ItemStack, ITEM_REGISTRY
from engine.gameplay.inventory import Inventory
from engine.gameplay.breaking import BlockBreaking, BlockBreakResult
from engine.gameplay.placement import BlockPlacement, PlacementResult
from engine.gameplay.drops import EntityItem, ItemDropManager
from engine.gameplay.crafting import (
    Ingredient, ShapedRecipe, ShapelessRecipe, RecipeManager, CraftingGrid,
)
from engine.gameplay.furnace import (
    FuelRegistry, SmeltingRecipe, SmeltingRecipeManager, Furnace,
)
from engine.gameplay.health import FoodProperties, FoodRegistry, HungerManager
from engine.gameplay.vanilla_foods import register_vanilla_food_items, register_vanilla_foods
from engine.gameplay.vanilla_fuels import register_vanilla_fuel_items, register_vanilla_fuels
from engine.gameplay.vanilla_smelting import register_vanilla_smelting_items, register_vanilla_smelting_recipes
from engine.gameplay.vanilla_food_recipes import register_vanilla_food_recipe_items, register_vanilla_food_recipes
from engine.gameplay.tools import ToolDefinition, ToolMaterial, ToolRegistry
from engine.gameplay.damage import DamageSource, ArmorDefinition, ArmorRegistry
from engine.gameplay.vanilla_armor import VANILLA_ARMOR_MATERIALS, create_vanilla_armor_registry
from engine.gameplay.vanilla_tools import VANILLA_TOOL_MATERIALS, create_vanilla_tool_registry
from engine.gameplay.time import GameRules, WorldTime
from engine.gameplay.player import PlayerController
from engine.gameplay.interaction import InteractionManager, BlockRayHit

__all__ = [
    "Item", "ItemRegistry", "ItemStack", "ITEM_REGISTRY",
    "Inventory",
    "BlockBreaking", "BlockBreakResult",
    "BlockPlacement", "PlacementResult",
    "EntityItem", "ItemDropManager",
    "Ingredient", "ShapedRecipe", "ShapelessRecipe", "RecipeManager", "CraftingGrid",
    "FuelRegistry", "SmeltingRecipe", "SmeltingRecipeManager", "Furnace",
    "FoodProperties", "FoodRegistry", "HungerManager",
    "register_vanilla_food_items", "register_vanilla_foods",
    "register_vanilla_fuel_items", "register_vanilla_fuels",
    "register_vanilla_smelting_items", "register_vanilla_smelting_recipes",
    "register_vanilla_food_recipe_items", "register_vanilla_food_recipes",
    "ToolDefinition", "ToolMaterial", "ToolRegistry",
    "DamageSource", "ArmorDefinition", "ArmorRegistry",
    "VANILLA_ARMOR_MATERIALS", "create_vanilla_armor_registry",
    "VANILLA_TOOL_MATERIALS", "create_vanilla_tool_registry",
    "GameRules", "WorldTime",
    "PlayerController", "InteractionManager", "BlockRayHit",
    "EffectType", "StatusEffect", "StatusEffectManager",
    "LootEntry", "BlockLootTable", "LootTableRegistry",
]

from engine.gameplay.effects import EffectType, StatusEffect, StatusEffectManager
from engine.gameplay.loot import LootEntry, BlockLootTable, LootTableRegistry
