"""Furnace fuel and smelting logic with explicit registries."""
from __future__ import annotations

import math

from engine.gameplay.crafting import Ingredient
from engine.gameplay.items import Item, ItemStack


class FuelRegistry:
    def __init__(self) -> None:
        self._burn_times: dict[Item, int] = {}

    def register(self, item: Item, burn_time: int) -> None:
        if not isinstance(item, Item):
            raise TypeError("fuel must be an Item")
        if isinstance(burn_time, bool) or not isinstance(burn_time, int) or burn_time <= 0:
            raise ValueError("burn_time must be a positive integer")
        self._burn_times[item] = burn_time

    def get_burn_time(self, stack: ItemStack) -> int:
        if not isinstance(stack, ItemStack) or stack.is_empty:
            return 0
        return self._burn_times.get(stack.item, 0)


class SmeltingRecipe:
    def __init__(self, ingredient: Ingredient, output: ItemStack, experience: float = 0.0) -> None:
        if not isinstance(ingredient, Ingredient):
            raise TypeError("ingredient must be an Ingredient")
        if not isinstance(output, ItemStack) or output.is_empty:
            raise ValueError("output must be a non-empty ItemStack")
        if output.count > output.item.max_stack_size:
            raise ValueError("output exceeds max_stack_size")
        if isinstance(experience, bool) or not isinstance(experience, (int, float)) or not math.isfinite(experience) or experience < 0:
            raise ValueError("experience must be a non-negative number")
        self.ingredient = ingredient
        self.output = output.copy()
        self.experience = float(experience)


class SmeltingRecipeManager:
    def __init__(self) -> None:
        self._recipes: list[SmeltingRecipe] = []

    def register(self, recipe: SmeltingRecipe) -> SmeltingRecipe:
        if not isinstance(recipe, SmeltingRecipe):
            raise TypeError("recipe must be a SmeltingRecipe")
        self._recipes.append(recipe)
        return recipe

    def find_recipe(self, stack: ItemStack) -> SmeltingRecipe | None:
        for recipe in self._recipes:
            if recipe.ingredient.matches(stack):
                return recipe
        return None


class Furnace:
    """Single-input, single-fuel, single-output furnace.

    The caller supplies a fuel registry and smelting recipe manager. Fuel
    container-item returns and experience-orb accounting are separate tasks.
    """

    DEFAULT_COOK_TIME = 200

    def __init__(self, fuels: FuelRegistry, recipes: SmeltingRecipeManager,
                 cook_time: int = DEFAULT_COOK_TIME) -> None:
        if not isinstance(cook_time, int) or isinstance(cook_time, bool) or cook_time <= 0:
            raise ValueError("cook_time must be a positive integer")
        self.fuels = fuels
        self.recipes = recipes
        self.input = ItemStack.empty()
        self.fuel = ItemStack.empty()
        self.output = ItemStack.empty()
        self.burn_time = 0
        self.current_item_burn_time = 0
        self.cook_time = 0
        self.total_cook_time = cook_time

    @property
    def is_burning(self) -> bool:
        return self.burn_time > 0

    def can_smelt(self) -> bool:
        recipe = self.recipes.find_recipe(self.input)
        if recipe is None:
            return False
        if self.output.is_empty:
            return recipe.output.count <= recipe.output.item.max_stack_size
        if not self.output.can_stack_with(recipe.output):
            return False
        return self.output.count + recipe.output.count <= self.output.item.max_stack_size

    def _consume_fuel(self) -> bool:
        duration = self.fuels.get_burn_time(self.fuel)
        if duration <= 0 or self.fuel.is_empty:
            return False
        self.current_item_burn_time = duration
        self.burn_time = duration
        self.fuel.shrink(1)
        return True

    def _smelt_once(self) -> bool:
        recipe = self.recipes.find_recipe(self.input)
        if recipe is None or not self.can_smelt():
            return False
        if self.output.is_empty:
            self.output = recipe.output.copy()
        else:
            self.output.count += recipe.output.count
        self.input.shrink(1)
        return True

    def update(self) -> bool:
        """Advance one furnace tick; return True if one item was smelted."""
        if self.burn_time > 0:
            self.burn_time -= 1

        if not self.is_burning and self.can_smelt():
            self._consume_fuel()

        smelted = False
        if self.is_burning and self.can_smelt():
            self.cook_time += 1
            if self.cook_time >= self.total_cook_time:
                self.cook_time = 0
                smelted = self._smelt_once()
        else:
            self.cook_time = 0

        # If the fuel ran out and no recipe can proceed, preserve remaining
        # burn ticks but expose the correct burning state through burn_time.
        return smelted


__all__ = ["FuelRegistry", "SmeltingRecipe", "SmeltingRecipeManager", "Furnace"]
