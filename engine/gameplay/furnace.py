"""Furnace fuel and smelting logic with explicit registries."""
from __future__ import annotations

import math

from engine.gameplay.crafting import Ingredient
from engine.gameplay.items import Item, ItemStack


class FuelRegistry:
    def __init__(self) -> None:
        self._burn_times: dict[tuple[Item, int | None], int] = {}

    def register(self, item: Item, burn_time: int, metadata: int | None = None) -> None:
        if not isinstance(item, Item):
            raise TypeError("fuel must be an Item")
        if isinstance(burn_time, bool) or not isinstance(burn_time, int) or burn_time <= 0:
            raise ValueError("burn_time must be a positive integer")
        if metadata is not None and (
            isinstance(metadata, bool) or not isinstance(metadata, int)
            or not 0 <= metadata <= 32767
        ):
            raise ValueError("metadata must be None or an integer from 0 to 32767")
        key = (item, metadata)
        if key in self._burn_times:
            raise ValueError(f"fuel already registered: {item.name} metadata={metadata}")
        self._burn_times[key] = burn_time

    def get_burn_time(self, stack: ItemStack) -> int:
        if not isinstance(stack, ItemStack) or stack.is_empty:
            return 0
        return self._burn_times.get(
            (stack.item, stack.metadata), self._burn_times.get((stack.item, None), 0)
        )


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
        self.container_returns: list[ItemStack] = []
        self.experience_pending = 0.0

    @property
    def is_burning(self) -> bool:
        return self.burn_time > 0

    @property
    def burn_progress(self) -> float:
        if self.current_item_burn_time <= 0:
            return 0.0
        return min(1.0, self.burn_time / self.current_item_burn_time)

    @property
    def cook_progress(self) -> float:
        return min(1.0, self.cook_time / self.total_cook_time)

    @staticmethod
    def _insert_stack(current: ItemStack, incoming: ItemStack) -> ItemStack:
        remainder = incoming.copy()
        if remainder.is_empty:
            return remainder
        if current.is_empty:
            moved = min(remainder.count, remainder.item.max_stack_size)
            current.item = remainder.item
            current.count = moved
            current.metadata = remainder.metadata
            current.damage = remainder.damage
            current.nbt = remainder.copy().nbt
            remainder.shrink(moved)
        else:
            current.merge_from(remainder)
        return remainder

    def insert_input(self, stack: ItemStack) -> ItemStack:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        return self._insert_stack(self.input, stack)

    def insert_fuel(self, stack: ItemStack) -> ItemStack:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if self.fuels.get_burn_time(stack) <= 0:
            return stack.copy()
        return self._insert_stack(self.fuel, stack)

    def take_container_returns(self) -> tuple[ItemStack, ...]:
        returned = tuple(stack.copy() for stack in self.container_returns)
        self.container_returns.clear()
        return returned

    def collect_experience(self, fraction_roll: float = 0.0) -> int:
        """Collect stored smelting XP using vanilla's fractional rounding rule."""
        if (isinstance(fraction_roll, bool)
                or not isinstance(fraction_roll, (int, float))
                or not math.isfinite(fraction_roll)
                or not 0.0 <= fraction_roll < 1.0):
            raise ValueError("fraction_roll must be in [0.0, 1.0)")
        whole = math.floor(self.experience_pending)
        fraction = self.experience_pending - whole
        amount = whole + (1 if fraction_roll < fraction else 0)
        self.experience_pending = 0.0
        return amount

    def take_output(self, amount: int | None = None) -> ItemStack:
        if amount is None:
            amount = self.output.count
        return self.output.split(amount)

    def take_output_with_experience(
        self, amount: int | None = None, fraction_roll: float = 0.0
    ) -> tuple[ItemStack, int]:
        """Extract output and collect all XP accumulated since the last collection."""
        extracted = self.take_output(amount)
        experience = self.collect_experience(fraction_roll) if not extracted.is_empty else 0
        return extracted, experience

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
        fuel_item = self.fuel.item
        self.fuel.shrink(1)
        if fuel_item.container_item is not None:
            returned = ItemStack(
                fuel_item.container_item, 1,
                metadata=fuel_item.container_item_metadata,
            )
            if self.fuel.is_empty:
                self.fuel = returned
            else:
                self.container_returns.append(returned)
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
        self.experience_pending += recipe.experience
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
