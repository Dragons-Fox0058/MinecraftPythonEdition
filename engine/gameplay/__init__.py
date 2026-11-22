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
    "GameRules", "WorldTime",
    "PlayerController", "InteractionManager", "BlockRayHit",
]
