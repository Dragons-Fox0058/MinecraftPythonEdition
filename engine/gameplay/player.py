"""Player-facing gameplay controller joining inventory and world actions."""
from __future__ import annotations

from engine.core import BlockPos, EnumFacing
from engine.gameplay.breaking import BlockBreaking
from engine.gameplay.crafting import CraftingGrid, RecipeManager
from engine.gameplay.drops import ItemDropManager
from engine.gameplay.health import FoodRegistry, HungerManager
from engine.gameplay.inventory import Inventory
from engine.gameplay.interaction import InteractionManager
from engine.gameplay.items import ItemStack
from engine.gameplay.placement import BlockPlacement
from engine.gameplay.tools import ToolRegistry


class PlayerController:
    """Gameplay facade attached to an existing EntityPlayer-like entity."""

    def __init__(self, entity, inventory: Inventory | None = None,
                 hunger: HungerManager | None = None,
                 difficulty: str = "normal", block_drop_resolver=None,
                 food_registry: FoodRegistry | None = None,
                 tool_registry: ToolRegistry | None = None) -> None:
        if not hasattr(entity, "world"):
            raise TypeError("entity must have a world")
        if difficulty not in ("peaceful", "easy", "normal", "hard"):
            raise ValueError("invalid difficulty")
        self.entity = entity
        self.world = entity.world
        self.inventory = inventory or Inventory()
        self.hunger = hunger or HungerManager()
        self.food_registry = food_registry if food_registry is not None else FoodRegistry()
        self.difficulty = difficulty
        self.death_processed = False
        self.tool_registry = tool_registry
        self.breaking = BlockBreaking(
            self.world, drop_resolver=block_drop_resolver, tool_registry=tool_registry
        )
        self.drops = ItemDropManager(self.world)
        self.interaction = InteractionManager(self.world)
        entity.inventory = self.inventory
        entity.hunger = self.hunger
        entity.gameplay_controller = self
        if entity not in self.world.entities:
            self.world.add_entity(entity)

    @property
    def held_item(self) -> ItemStack:
        return self.inventory.selected_item

    def select_hotbar_slot(self, index: int) -> None:
        self.inventory.select_hotbar_slot(index)

    def tick(self) -> None:
        self.hunger.tick(
            self.entity,
            natural_regeneration=self.world.game_rules.get_bool("naturalRegeneration"),
            difficulty=self.difficulty,
        )

    def consume_food(self) -> bool:
        consumed = self.hunger.consume(self.held_item, self.food_registry)
        if consumed:
            for returned in self.hunger.take_container_returns():
                remainder = self.inventory.insert(returned)
                if not remainder.is_empty:
                    self.drops.spawn(
                        self.entity.pos.x, self.entity.pos.y + 0.5,
                        self.entity.pos.z, remainder,
                    )
        return consumed

    def eat(self, food_points: int, saturation_modifier: float) -> None:
        self.hunger.eat(food_points, saturation_modifier)

    def add_exhaustion(self, amount: float) -> None:
        self.hunger.add_exhaustion(amount)

    def ray_trace_blocks(self, start, direction, max_distance: float = 5.0):
        return self.interaction.ray_trace_blocks(start, direction, max_distance)

    def break_block(self, pos: BlockPos, dig_speed: float = 1.0,
                    can_harvest: bool = False):
        return self.breaking.damage_block(
            pos, dig_speed, can_harvest, tool_stack=self.held_item
        )

    def place_block(self, clicked_pos: BlockPos, face: EnumFacing,
                    block_resolver, can_place=None):
        return BlockPlacement(self.world, block_resolver).place(
            self.held_item, clicked_pos, face, can_place
        )

    def craft(self, grid: CraftingGrid, recipes: RecipeManager) -> ItemStack:
        return grid.craft(recipes)

    def craft_to_inventory(self, grid: CraftingGrid, recipes: RecipeManager) -> ItemStack:
        """Craft once, collect the result and overflow container items into the world."""
        output = grid.craft(recipes)
        if output.is_empty:
            return output

        remainder = self.inventory.insert(output)
        if not remainder.is_empty:
            self.drops.spawn(
                self.entity.pos.x, self.entity.pos.y + 0.5,
                self.entity.pos.z, remainder,
            )

        for returned in grid.take_container_returns():
            remainder = self.inventory.insert(returned)
            if not remainder.is_empty:
                self.drops.spawn(
                    self.entity.pos.x, self.entity.pos.y + 0.5,
                    self.entity.pos.z, remainder,
                )
        return output

    def drop_item(self, stack: ItemStack, x: float | None = None,
                  y: float | None = None, z: float | None = None):
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if stack.is_empty:
            return None
        x = self.entity.pos.x if x is None else x
        y = self.entity.pos.y + 0.5 if y is None else y
        z = self.entity.pos.z if z is None else z
        dropped_stack = stack.copy()
        entity = self.drops.spawn(x, y, z, dropped_stack)
        stack.shrink(stack.count)
        return entity

    def try_pickup(self, item_entity) -> bool:
        return item_entity.try_pickup(self.inventory)

    def on_death(self) -> tuple:
        """Drop carried items once unless keepInventory is enabled."""
        if self.death_processed:
            return ()
        self.death_processed = True
        if (self.world.game_rules.get_bool("keepInventory")
                or not self.world.game_rules.get_bool("doEntityDrops")):
            return ()
        spawned = []
        carried = list(self.inventory.slots) + list(self.inventory.armor) + [self.inventory.offhand]
        for stack in carried:
            if not stack.is_empty:
                entity = self.drop_item(stack)
                if entity is not None:
                    spawned.append(entity)
        return tuple(spawned)


__all__ = ["PlayerController"]
