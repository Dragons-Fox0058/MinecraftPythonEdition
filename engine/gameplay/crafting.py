"""Shaped and shapeless crafting recipes for 2x2 and 3x3 grids."""
from __future__ import annotations

from typing import Iterable

from engine.gameplay.items import Item, ItemStack


class Ingredient:
    """One-of item ingredient, optionally constrained to one metadata value."""

    __slots__ = ("items", "metadata")

    def __init__(self, item: Item | Iterable[Item], metadata: int | None = None) -> None:
        if isinstance(item, Item):
            items = (item,)
        else:
            try:
                items = tuple(item)
            except TypeError as exc:
                raise TypeError("ingredient must be an Item or iterable of Items") from exc
        if not items or any(not isinstance(candidate, Item) for candidate in items):
            raise TypeError("ingredient must contain one or more Item values")
        items = tuple(dict.fromkeys(items))
        if metadata is not None and (
            isinstance(metadata, bool) or not isinstance(metadata, int)
            or not 0 <= metadata <= 32767
        ):
            raise ValueError("metadata must be None or an integer from 0 to 32767")
        self.items = items
        self.metadata = metadata

    @property
    def item(self) -> Item | None:
        """Return the sole item for single-choice ingredients, else None."""
        return self.items[0] if len(self.items) == 1 else None

    @classmethod
    def any_of(cls, *items: Item, metadata: int | None = None) -> "Ingredient":
        return cls(items, metadata=metadata)

    def matches(self, stack: ItemStack) -> bool:
        return (
            not stack.is_empty
            and stack.item in self.items
            and (self.metadata is None or stack.metadata == self.metadata)
        )


class ShapedRecipe:
    def __init__(self, width: int, height: int, ingredients: Iterable[Ingredient | None],
                 output: ItemStack, mirrored: bool = True) -> None:
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ValueError("width must be a positive integer")
        if isinstance(height, bool) or not isinstance(height, int) or height < 1:
            raise ValueError("height must be a positive integer")
        cells = tuple(ingredients)
        if len(cells) != width * height:
            raise ValueError("ingredient count must equal width * height")
        if any(cell is not None and not isinstance(cell, Ingredient) for cell in cells):
            raise TypeError("ingredients must be Ingredient or None")
        if not isinstance(output, ItemStack) or output.is_empty:
            raise ValueError("recipe output must be a non-empty ItemStack")
        if output.count > output.item.max_stack_size:
            raise ValueError("recipe output exceeds max_stack_size")
        if not isinstance(mirrored, bool):
            raise ValueError("mirrored must be a bool")
        self.width = width
        self.height = height
        self.ingredients = cells
        self.output = output.copy()
        self.mirrored = mirrored

    def matches(self, grid: "CraftingGrid") -> bool:
        if self.width > grid.width or self.height > grid.height:
            return False
        for offset_y in range(grid.height - self.height + 1):
            for offset_x in range(grid.width - self.width + 1):
                if self._matches_at(grid, offset_x, offset_y, False):
                    return True
                if self.mirrored and self._matches_at(grid, offset_x, offset_y, True):
                    return True
        return False

    def _matches_at(self, grid: "CraftingGrid", offset_x: int, offset_y: int,
                    mirrored: bool) -> bool:
        for y in range(grid.height):
            for x in range(grid.width):
                rx, ry = x - offset_x, y - offset_y
                ingredient = None
                if 0 <= rx < self.width and 0 <= ry < self.height:
                    if mirrored:
                        rx = self.width - 1 - rx
                    ingredient = self.ingredients[ry * self.width + rx]
                stack = grid.get_slot(y * grid.width + x)
                if ingredient is None:
                    if not stack.is_empty:
                        return False
                elif not ingredient.matches(stack):
                    return False
        return True


class ShapelessRecipe:
    def __init__(self, ingredients: Iterable[Ingredient], output: ItemStack) -> None:
        self.ingredients = tuple(ingredients)
        if not self.ingredients or any(not isinstance(i, Ingredient) for i in self.ingredients):
            raise ValueError("shapeless recipe needs one or more Ingredient values")
        if len(self.ingredients) > 9:
            raise ValueError("a 3x3 crafting grid cannot hold more than 9 ingredients")
        if not isinstance(output, ItemStack) or output.is_empty:
            raise ValueError("recipe output must be a non-empty ItemStack")
        if output.count > output.item.max_stack_size:
            raise ValueError("recipe output exceeds max_stack_size")
        self.output = output.copy()

    def matches(self, grid: "CraftingGrid") -> bool:
        occupied = [s for s in grid.slots if not s.is_empty]
        if len(occupied) != len(self.ingredients):
            return False
        # Backtracking avoids greedy-match errors with wildcard metadata.
        ordered = sorted(self.ingredients, key=lambda i: i.metadata is None)

        def assign(index: int, remaining: tuple[int, ...]) -> bool:
            if index == len(ordered):
                return True
            ingredient = ordered[index]
            for candidate in remaining:
                if ingredient.matches(occupied[candidate]):
                    next_remaining = tuple(i for i in remaining if i != candidate)
                    if assign(index + 1, next_remaining):
                        return True
            return False

        return assign(0, tuple(range(len(occupied))))


class RecipeManager:
    def __init__(self) -> None:
        self._recipes: list[ShapedRecipe | ShapelessRecipe] = []

    def register(self, recipe: ShapedRecipe | ShapelessRecipe):
        if not isinstance(recipe, (ShapedRecipe, ShapelessRecipe)):
            raise TypeError("recipe must be shaped or shapeless")
        self._recipes.append(recipe)
        return recipe

    def find_matching_recipe(self, grid: "CraftingGrid"):
        for recipe in self._recipes:
            if recipe.matches(grid):
                return recipe
        return None

    def __len__(self) -> int:
        return len(self._recipes)


class CraftingGrid:
    def __init__(self, width: int = 3, height: int = 3) -> None:
        if any(isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 3
               for v in (width, height)):
            raise ValueError("crafting grid dimensions must be between 1 and 3")
        self.width = width
        self.height = height
        self.slots = [ItemStack.empty() for _ in range(width * height)]

    def get_slot(self, index: int) -> ItemStack:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self.slots):
            raise IndexError("crafting slot index out of range")
        return self.slots[index]

    def set_slot(self, index: int, stack: ItemStack) -> None:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not stack.is_empty and stack.count > stack.item.max_stack_size:
            raise ValueError("stack exceeds max_stack_size")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self.slots):
            raise IndexError("crafting slot index out of range")
        self.slots[index] = stack.copy()

    def find_recipe(self, manager: RecipeManager):
        return manager.find_matching_recipe(self)

    def craft(self, manager: RecipeManager) -> ItemStack:
        recipe = manager.find_matching_recipe(self)
        if recipe is None:
            return ItemStack.empty()
        output = recipe.output.copy()
        for stack in self.slots:
            if not stack.is_empty:
                stack.shrink(1)
        return output

    def clear(self) -> None:
        self.slots = [ItemStack.empty() for _ in self.slots]


__all__ = [
    "Ingredient", "ShapedRecipe", "ShapelessRecipe",
    "RecipeManager", "CraftingGrid",
]
