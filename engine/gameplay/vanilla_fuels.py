"""Source-derived non-weapon furnace fuel catalogue for Java 1.12.2."""
from __future__ import annotations

from engine.gameplay.furnace import FuelRegistry
from engine.gameplay.items import ITEM_REGISTRY, Item, ItemRegistry


def register_vanilla_fuel_items(
    registry: ItemRegistry = ITEM_REGISTRY,
) -> dict[str, Item]:
    """Register the item identities needed by the vanilla furnace fuel table."""
    if not isinstance(registry, ItemRegistry):
        raise TypeError("registry must be an ItemRegistry")

    bucket = registry.get_by_name("minecraft:bucket")
    if bucket is None:
        bucket = Item(325, "minecraft:bucket", max_stack_size=16)
    definitions = (
        (325, "minecraft:bucket", 16, False, None),
        (5, "minecraft:planks", 64, True, None),
        (6, "minecraft:sapling", 64, True, None),
        (17, "minecraft:log", 64, True, None),
        (25, "minecraft:noteblock", 64, False, None),
        (35, "minecraft:wool", 64, True, None),
        (47, "minecraft:bookshelf", 64, False, None),
        (53, "minecraft:wooden_stairs", 64, False, None),
        (54, "minecraft:chest", 64, False, None),
        (58, "minecraft:crafting_table", 64, False, None),
        (65, "minecraft:ladder", 64, False, None),
        (72, "minecraft:wooden_pressure_plate", 64, False, None),
        (84, "minecraft:jukebox", 64, False, None),
        (85, "minecraft:fence", 64, False, None),
        (96, "minecraft:trapdoor", 64, False, None),
        (107, "minecraft:fence_gate", 64, True, None),
        (126, "minecraft:wooden_slab", 64, True, None),
        (143, "minecraft:wooden_button", 64, False, None),
        (162, "minecraft:log2", 64, True, None),
        (171, "minecraft:carpet", 64, True, None),
        (173, "minecraft:coal_block", 64, False, None),
        (263, "minecraft:coal", 64, True, None),
        (280, "minecraft:stick", 64, False, None),
        (281, "minecraft:bowl", 64, False, None),
        (323, "minecraft:sign", 16, False, None),
        (324, "minecraft:wooden_door", 64, False, None),
        (327, "minecraft:lava_bucket", 1, False, "minecraft:bucket"),
        (333, "minecraft:boat", 1, False, None),
        (369, "minecraft:blaze_rod", 64, False, None),
        (427, "minecraft:spruce_door", 64, False, None),
        (428, "minecraft:birch_door", 64, False, None),
        (429, "minecraft:jungle_door", 64, False, None),
        (430, "minecraft:acacia_door", 64, False, None),
        (431, "minecraft:dark_oak_door", 64, False, None),
        (444, "minecraft:spruce_boat", 1, False, None),
        (445, "minecraft:birch_boat", 1, False, None),
        (446, "minecraft:jungle_boat", 1, False, None),
        (447, "minecraft:acacia_boat", 1, False, None),
        (448, "minecraft:dark_oak_boat", 1, False, None),
    )

    result: dict[str, Item] = {}
    for item_id, name, stack_size, subtypes, container_name in definitions:
        existing_id = registry.get_by_id(item_id)
        existing_name = registry.get_by_name(name)
        if existing_id is not None or existing_name is not None:
            if existing_id is None or existing_name is not existing_id:
                raise ValueError(f"conflicting item registry entry for {name} ({item_id})")
            if (existing_id.item_id != item_id or existing_id.name != name
                    or existing_id.max_stack_size != stack_size):
                raise ValueError(f"incompatible item definition already registered: {name}")
            item = existing_id
        else:
            container = registry.get_by_name(container_name) if container_name else None
            item = Item(
                item_id, name, max_stack_size=stack_size,
                has_subtypes=subtypes, container_item=container,
            )
            registry.register(item)
        result[name] = item

    lava_bucket = result["minecraft:lava_bucket"]
    if lava_bucket.container_item is None:
        lava_bucket.container_item = result["minecraft:bucket"]
    elif lava_bucket.container_item is not result["minecraft:bucket"]:
        raise ValueError("incompatible lava bucket container item")
    return result


def register_vanilla_fuels(
    item_registry: ItemRegistry = ITEM_REGISTRY,
    fuel_registry: FuelRegistry | None = None,
) -> FuelRegistry:
    """Populate the 1.12.2 furnace fuel durations for supported non-weapon fuels."""
    items = register_vanilla_fuel_items(item_registry)
    fuels = fuel_registry if fuel_registry is not None else FuelRegistry()

    fuels.register(items["minecraft:wooden_slab"], 150)
    fuels.register(items["minecraft:wool"], 100)
    fuels.register(items["minecraft:carpet"], 67)
    fuels.register(items["minecraft:ladder"], 300)
    fuels.register(items["minecraft:wooden_button"], 100)

    for name in (
        "minecraft:planks", "minecraft:log", "minecraft:log2",
        "minecraft:noteblock", "minecraft:bookshelf", "minecraft:wooden_stairs",
        "minecraft:chest", "minecraft:crafting_table", "minecraft:wooden_pressure_plate",
        "minecraft:fence",
        "minecraft:trapdoor", "minecraft:fence_gate",
    ):
        fuels.register(items[name], 300)

    fuels.register(items["minecraft:coal_block"], 16000)
    fuels.register(items["minecraft:stick"], 100)
    fuels.register(items["minecraft:sign"], 200)
    fuels.register(items["minecraft:coal"], 1600, metadata=0)
    fuels.register(items["minecraft:coal"], 1600, metadata=1)  # charcoal
    fuels.register(items["minecraft:lava_bucket"], 20000)
    fuels.register(items["minecraft:sapling"], 100)
    fuels.register(items["minecraft:bowl"], 100)
    fuels.register(items["minecraft:blaze_rod"], 2400)

    for name in (
        "minecraft:wooden_door", "minecraft:spruce_door",
        "minecraft:birch_door", "minecraft:jungle_door",
        "minecraft:acacia_door", "minecraft:dark_oak_door",
    ):
        fuels.register(items[name], 200)

    for name in (
        "minecraft:boat", "minecraft:spruce_boat", "minecraft:birch_boat",
        "minecraft:jungle_boat", "minecraft:acacia_boat", "minecraft:dark_oak_boat",
    ):
        fuels.register(items[name], 400)

    return fuels


__all__ = ["register_vanilla_fuel_items", "register_vanilla_fuels"]
