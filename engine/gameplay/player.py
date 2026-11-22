"""Player-facing gameplay controller joining inventory and world actions."""
from __future__ import annotations

import math

from engine.core import BlockPos, EnumFacing
from engine.gameplay.breaking import BlockBreaking
from engine.gameplay.crafting import CraftingGrid, RecipeManager
from engine.gameplay.drops import ItemDropManager
from engine.gameplay.damage import ArmorRegistry, DamageSource
from engine.gameplay.health import FoodRegistry, HungerManager
from engine.gameplay.inventory import Inventory
from engine.gameplay.interaction import InteractionManager
from engine.gameplay.items import ItemStack
from engine.gameplay.loot import LootTableRegistry
from engine.gameplay.placement import BlockPlacement
from engine.gameplay.tools import ToolRegistry
from engine.gameplay.game_mode import GameMode, stack_has_block_restriction


class PlayerController:
    """Gameplay facade attached to an existing EntityPlayer-like entity."""

    def __init__(self, entity, inventory: Inventory | None = None,
                 hunger: HungerManager | None = None,
                 difficulty: str = "normal", block_drop_resolver=None,
                 food_registry: FoodRegistry | None = None,
                 tool_registry: ToolRegistry | None = None,
                 armor_registry: ArmorRegistry | None = None,
                 loot_registry: LootTableRegistry | None = None,
                 game_mode: GameMode | int | str | None = None) -> None:
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
        self.game_mode = GameMode.parse(game_mode if game_mode is not None else getattr(self.world, "default_game_mode", GameMode.SURVIVAL))
        self.death_processed = False
        self.tool_registry = tool_registry
        if armor_registry is not None and not isinstance(armor_registry, ArmorRegistry):
            raise TypeError("armor_registry must be an ArmorRegistry or None")
        self.armor_registry = armor_registry
        self.breaking = BlockBreaking(
            self.world, drop_resolver=block_drop_resolver, tool_registry=tool_registry,
            loot_registry=loot_registry
        )
        self.drops = ItemDropManager(self.world)
        self.interaction = InteractionManager(self.world)
        entity.inventory = self.inventory
        entity.hunger = self.hunger
        entity.gameplay_controller = self
        self._apply_game_mode_flags()
        if entity not in self.world.entities:
            self.world.add_entity(entity)

    @property
    def held_item(self) -> ItemStack:
        return self.inventory.selected_item

    def select_hotbar_slot(self, index: int) -> None:
        self.inventory.select_hotbar_slot(index)

    def _apply_game_mode_flags(self) -> None:
        self.entity.no_clip = self.game_mode is GameMode.SPECTATOR
        self.entity.is_flying = self.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR)

    def set_game_mode(self, mode: GameMode | int | str) -> GameMode:
        self.game_mode = GameMode.parse(mode)
        self._apply_game_mode_flags()
        self.entity.motion = type(self.entity.motion)(0.0, 0.0, 0.0)
        self.death_processed = False
        return self.game_mode

    def execute_command(self, command: str) -> str:
        """Execute the local player's supported vanilla-style /gamemode command."""
        if not isinstance(command, str):
            raise TypeError("command must be a string")
        parts = command.strip().split()
        if parts and parts[0].startswith("/"):
            parts[0] = parts[0][1:]
        if not parts or parts[0].lower() != "gamemode":
            return "Unknown command"
        if len(parts) not in (2, 3):
            return "Usage: /gamemode <survival|creative|adventure|spectator|0-3> [player]"
        if len(parts) == 3 and parts[2] not in ("@s", getattr(self.entity, "name", "")):
            return "This single-player session can only change your own game mode"
        try:
            mode = self.set_game_mode(parts[1])
        except ValueError:
            return "Unknown game mode. Use survival, creative, adventure, spectator, or 0-3."
        return f"Set own game mode to {mode.display_name}"

    def can_break_block(self, block_name: str, stack: ItemStack | None = None) -> bool:
        if self.game_mode is GameMode.SPECTATOR:
            return False
        if self.game_mode is GameMode.ADVENTURE:
            return stack_has_block_restriction(stack, "CanDestroy", block_name)
        return True

    def can_place_block(self, block_name: str, stack: ItemStack | None = None) -> bool:
        if self.game_mode is GameMode.SPECTATOR:
            return False
        if self.game_mode is GameMode.ADVENTURE:
            return stack_has_block_restriction(stack, "CanPlaceOn", block_name)
        return True

    def tick(self) -> None:
        if self.game_mode not in (GameMode.SURVIVAL, GameMode.ADVENTURE):
            return
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

    def damage(self, amount: float, source: DamageSource | None = None) -> bool:
        """Apply damage through equipped armor; return whether health decreased."""
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError("amount must be finite and non-negative")
        if source is None:
            source = DamageSource("generic")
        if not isinstance(source, DamageSource):
            raise TypeError("source must be a DamageSource")
        if self.entity.dead:
            return False
        if self.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR) and source.name not in ("void", "out_of_world", "outOfWorld"):
            return False
        armor_stacks = tuple(self.inventory.armor)
        if self.armor_registry is not None:
            reduced = self.armor_registry.calculate_damage(amount, armor_stacks, source)
        else:
            reduced = amount
        if reduced <= 0:
            return False
        before = self.entity.health
        accepted = self.entity.damage(reduced)
        if accepted is False:
            return False
        if self.armor_registry is not None:
            self.armor_registry.damage_armor(amount, armor_stacks, source)
        return self.entity.health < before

    def eat(self, food_points: int, saturation_modifier: float) -> None:
        self.hunger.eat(food_points, saturation_modifier)

    def add_exhaustion(self, amount: float) -> None:
        self.hunger.add_exhaustion(amount)

    def ray_trace_blocks(self, start, direction, max_distance: float = 5.0):
        return self.interaction.ray_trace_blocks(start, direction, max_distance)

    def break_block(self, pos: BlockPos, dig_speed: float = 1.0,
                    can_harvest: bool = False):
        if not self.can_break_block(self.world.get_block_state(pos).block.registry_name, self.held_item):
            return None
        creative = self.game_mode is GameMode.CREATIVE
        return self.breaking.damage_block(
            pos, dig_speed=dig_speed, can_harvest=(True if creative else can_harvest),
            tool_stack=(None if creative else self.held_item),
            instant=creative, drop_items=not creative,
        )

    def place_block(self, clicked_pos: BlockPos, face: EnumFacing,
                    block_resolver, can_place=None):
        held = self.held_item
        if self.game_mode is GameMode.SPECTATOR:
            return None
        if self.game_mode is GameMode.ADVENTURE:
            clicked = self.world.get_block_state(clicked_pos).block.registry_name
            if not self.can_place_block(clicked, held):
                return None
        return BlockPlacement(self.world, block_resolver).place(
            held, clicked_pos, face, can_place,
            consume=self.game_mode is not GameMode.CREATIVE,
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
        if self.game_mode is GameMode.SPECTATOR or stack.is_empty:
            return None
        x = self.entity.pos.x if x is None else x
        y = self.entity.pos.y + 0.5 if y is None else y
        z = self.entity.pos.z if z is None else z
        dropped_stack = stack.copy()
        entity = self.drops.spawn(x, y, z, dropped_stack)
        stack.shrink(stack.count)
        return entity

    def try_pickup(self, item_entity) -> bool:
        return False if self.game_mode is GameMode.SPECTATOR else item_entity.try_pickup(self.inventory)

    def on_death(self) -> tuple:
        """Drop carried items once unless keepInventory is enabled."""
        if self.death_processed:
            return ()
        self.death_processed = True
        if (self.game_mode in (GameMode.CREATIVE, GameMode.SPECTATOR)
                or self.world.game_rules.get_bool("keepInventory")
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
