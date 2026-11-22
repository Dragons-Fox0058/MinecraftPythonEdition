"""Verified food item definitions for Minecraft Java Edition 1.12.2.

Numeric IDs and item behavior are transcribed from the 1.12.2 MCP
decompiled source (net.minecraft.item.Item, ItemFood, ItemSoup,
ItemFishFood, ItemAppleGold, and ItemChorusFruit). This module is explicit:
importing it does not mutate global registries.
"""
from __future__ import annotations

from engine.gameplay.health import FoodProperties, FoodRegistry
from engine.gameplay.items import ITEM_REGISTRY, Item, ItemRegistry


def register_vanilla_food_items(
    registry: ItemRegistry = ITEM_REGISTRY,
) -> dict[str, Item]:
    """Register food items plus their bowl container in the supplied registry."""
    if not isinstance(registry, ItemRegistry):
        raise TypeError("registry must be an ItemRegistry")

    definitions = (
        (281, "minecraft:bowl", 64, None),
        (260, "minecraft:apple", 64, None),
        (282, "minecraft:mushroom_stew", 1, "minecraft:bowl"),
        (297, "minecraft:bread", 64, None),
        (319, "minecraft:porkchop", 64, None),
        (320, "minecraft:cooked_porkchop", 64, None),
        (322, "minecraft:golden_apple", 64, None),
        (349, "minecraft:fish", 64, None),
        (350, "minecraft:cooked_fish", 64, None),
        (357, "minecraft:cookie", 64, None),
        (360, "minecraft:melon", 64, None),
        (363, "minecraft:beef", 64, None),
        (364, "minecraft:cooked_beef", 64, None),
        (365, "minecraft:chicken", 64, None),
        (366, "minecraft:cooked_chicken", 64, None),
        (367, "minecraft:rotten_flesh", 64, None),
        (375, "minecraft:spider_eye", 64, None),
        (391, "minecraft:carrot", 64, None),
        (392, "minecraft:potato", 64, None),
        (393, "minecraft:baked_potato", 64, None),
        (394, "minecraft:poisonous_potato", 64, None),
        (396, "minecraft:golden_carrot", 64, None),
        (400, "minecraft:pumpkin_pie", 64, None),
        (411, "minecraft:rabbit", 64, None),
        (412, "minecraft:cooked_rabbit", 64, None),
        (413, "minecraft:rabbit_stew", 1, "minecraft:bowl"),
        (423, "minecraft:mutton", 64, None),
        (424, "minecraft:cooked_mutton", 64, None),
        (432, "minecraft:chorus_fruit", 64, None),
        (434, "minecraft:beetroot", 64, None),
        (436, "minecraft:beetroot_soup", 1, "minecraft:bowl"),
    )

    created: dict[str, Item] = {}
    for item_id, name, stack_size, _ in definitions:
        existing_id = registry.get_by_id(item_id)
        existing_name = registry.get_by_name(name)
        if existing_id is not None or existing_name is not None:
            if existing_id is None or existing_name is not existing_id:
                raise ValueError(f"conflicting item registry entry for {name} ({item_id})")
            if (existing_id.item_id != item_id
                    or existing_id.name != name
                    or existing_id.max_stack_size != stack_size):
                raise ValueError(f"incompatible item definition already registered: {name}")
            created[name] = existing_id
        else:
            item = Item(item_id, name, max_stack_size=stack_size)
            registry.register(item)
            created[name] = item

    for item_id, name, stack_size, container_name in definitions:
        if container_name is not None:
            item = created[name]
            container = created[container_name]
            if item.container_item is None:
                item.container_item = container
            elif item.container_item is not container:
                raise ValueError(f"incompatible container item for {name}")

    return created


def register_vanilla_foods(
    item_registry: ItemRegistry = ITEM_REGISTRY,
    food_registry: FoodRegistry | None = None,
) -> FoodRegistry:
    """Populate food values and metadata variants from the 1.12.2 item classes."""
    items = register_vanilla_food_items(item_registry)
    foods = food_registry if food_registry is not None else FoodRegistry()

    def add(name: str, points: int, saturation: float,
            metadata: int | None = None, always_edible: bool = False) -> None:
        foods.register(
            items[name],
            FoodProperties(points, saturation, always_edible=always_edible),
            metadata=metadata,
        )

    add("minecraft:apple", 4, 0.3)
    add("minecraft:mushroom_stew", 6, 0.6)
    add("minecraft:bread", 5, 0.6)
    add("minecraft:porkchop", 3, 0.3)
    add("minecraft:cooked_porkchop", 8, 0.8)
    add("minecraft:golden_apple", 4, 1.2, metadata=0, always_edible=True)
    add("minecraft:golden_apple", 4, 1.2, metadata=1, always_edible=True)

    # ItemFishFood.FishType values from the 1.12.2 source.
    add("minecraft:fish", 2, 0.1, metadata=0)  # cod
    add("minecraft:fish", 2, 0.1, metadata=1)  # salmon
    add("minecraft:fish", 1, 0.1, metadata=2)  # clownfish
    add("minecraft:fish", 1, 0.1, metadata=3)  # pufferfish
    add("minecraft:cooked_fish", 5, 0.6, metadata=0)  # cooked cod
    add("minecraft:cooked_fish", 6, 0.8, metadata=1)  # cooked salmon

    add("minecraft:cookie", 2, 0.1)
    add("minecraft:melon", 2, 0.3)
    add("minecraft:beef", 3, 0.3)
    add("minecraft:cooked_beef", 8, 0.8)
    add("minecraft:chicken", 2, 0.3)
    add("minecraft:cooked_chicken", 6, 0.6)
    add("minecraft:rotten_flesh", 4, 0.1)
    add("minecraft:spider_eye", 2, 0.8)
    add("minecraft:carrot", 3, 0.6)
    add("minecraft:potato", 1, 0.3)
    add("minecraft:baked_potato", 5, 0.6)
    add("minecraft:poisonous_potato", 2, 0.3)
    add("minecraft:golden_carrot", 6, 1.2)
    add("minecraft:pumpkin_pie", 8, 0.3)
    add("minecraft:rabbit", 3, 0.3)
    add("minecraft:cooked_rabbit", 5, 0.6)
    add("minecraft:rabbit_stew", 10, 0.6)
    add("minecraft:mutton", 2, 0.3)
    add("minecraft:cooked_mutton", 6, 0.8)
    add("minecraft:chorus_fruit", 4, 0.3, always_edible=True)
    add("minecraft:beetroot", 1, 0.6)
    add("minecraft:beetroot_soup", 6, 0.6)

    return foods


__all__ = ["register_vanilla_food_items", "register_vanilla_foods"]
