"""Source-derived non-weapon vanilla furnace recipes for Java 1.12.2."""
from __future__ import annotations

from engine.gameplay.crafting import Ingredient
from engine.gameplay.furnace import SmeltingRecipe, SmeltingRecipeManager
from engine.gameplay.items import ITEM_REGISTRY, Item, ItemRegistry, ItemStack


def register_vanilla_smelting_items(
    registry: ItemRegistry = ITEM_REGISTRY,
) -> dict[str, Item]:
    """Register item identities required by the supported vanilla smelting table."""
    if not isinstance(registry, ItemRegistry):
        raise TypeError("registry must be an ItemRegistry")

    definitions = (
        (1, "minecraft:stone", 64, False),
        (4, "minecraft:cobblestone", 64, False),
        (12, "minecraft:sand", 64, False),
        (14, "minecraft:gold_ore", 64, False),
        (15, "minecraft:iron_ore", 64, False),
        (16, "minecraft:coal_ore", 64, False),
        (17, "minecraft:log", 64, True),
        (19, "minecraft:sponge", 64, True),
        (20, "minecraft:glass", 64, False),
        (21, "minecraft:lapis_ore", 64, False),
        (56, "minecraft:diamond_ore", 64, False),
        (73, "minecraft:redstone_ore", 64, False),
        (81, "minecraft:cactus", 64, False),
        (82, "minecraft:clay", 64, False),
        (87, "minecraft:netherrack", 64, False),
        (98, "minecraft:stonebrick", 64, True),
        (129, "minecraft:emerald_ore", 64, False),
        (153, "minecraft:quartz_ore", 64, False),
        (159, "minecraft:stained_hardened_clay", 64, True),
        (162, "minecraft:log2", 64, True),
        (172, "minecraft:hardened_clay", 64, False),
        (235, "minecraft:white_glazed_terracotta", 64, False),
        (236, "minecraft:orange_glazed_terracotta", 64, False),
        (237, "minecraft:magenta_glazed_terracotta", 64, False),
        (238, "minecraft:light_blue_glazed_terracotta", 64, False),
        (239, "minecraft:yellow_glazed_terracotta", 64, False),
        (240, "minecraft:lime_glazed_terracotta", 64, False),
        (241, "minecraft:pink_glazed_terracotta", 64, False),
        (242, "minecraft:gray_glazed_terracotta", 64, False),
        (243, "minecraft:light_gray_glazed_terracotta", 64, False),
        (244, "minecraft:cyan_glazed_terracotta", 64, False),
        (245, "minecraft:purple_glazed_terracotta", 64, False),
        (246, "minecraft:blue_glazed_terracotta", 64, False),
        (247, "minecraft:brown_glazed_terracotta", 64, False),
        (248, "minecraft:green_glazed_terracotta", 64, False),
        (249, "minecraft:red_glazed_terracotta", 64, False),
        (250, "minecraft:black_glazed_terracotta", 64, False),
        (263, "minecraft:coal", 64, True),
        (264, "minecraft:diamond", 64, False),
        (265, "minecraft:iron_ingot", 64, False),
        (266, "minecraft:gold_ingot", 64, False),
        (331, "minecraft:redstone", 64, False),
        (336, "minecraft:brick", 64, False),
        (337, "minecraft:clay_ball", 64, False),
        (349, "minecraft:fish", 64, True),
        (350, "minecraft:cooked_fish", 64, True),
        (351, "minecraft:dye", 64, True),
        (364, "minecraft:cooked_beef", 64, False),
        (366, "minecraft:cooked_chicken", 64, False),
        (388, "minecraft:emerald", 64, False),
        (393, "minecraft:baked_potato", 64, False),
        (405, "minecraft:netherbrick", 64, False),
        (406, "minecraft:quartz", 64, False),
        (433, "minecraft:chorus_fruit_popped", 64, False),
    )

    result: dict[str, Item] = {}
    for item_id, name, stack_size, subtypes in definitions:
        existing_id = registry.get_by_id(item_id)
        existing_name = registry.get_by_name(name)
        if existing_id is not None or existing_name is not None:
            if existing_id is None or existing_name is not existing_id:
                raise ValueError(f"conflicting item registry entry for {name} ({item_id})")
            if existing_id.max_stack_size != stack_size:
                raise ValueError(f"incompatible stack size for existing item {name}")
            item = existing_id
            if subtypes:
                item.has_subtypes = True
        else:
            item = Item(item_id, name, max_stack_size=stack_size, has_subtypes=subtypes)
            registry.register(item)
        result[name] = item

    # Reuse food items already registered by the food catalogue.
    from engine.gameplay.vanilla_foods import register_vanilla_food_items
    result.update(register_vanilla_food_items(registry))
    return result


def register_vanilla_smelting_recipes(
    item_registry: ItemRegistry = ITEM_REGISTRY,
    recipe_manager: SmeltingRecipeManager | None = None,
) -> SmeltingRecipeManager:
    """Register supported non-weapon 1.12.2 furnace recipes and XP values."""
    items = register_vanilla_smelting_items(item_registry)
    recipes = recipe_manager if recipe_manager is not None else SmeltingRecipeManager()

    def add(input_name: str, output_name: str, xp: float,
            input_meta: int | None = None, output_meta: int = 0) -> None:
        recipes.register(SmeltingRecipe(
            Ingredient(items[input_name], metadata=input_meta),
            ItemStack(items[output_name], 1, metadata=output_meta),
            experience=xp,
        ))

    add("minecraft:iron_ore", "minecraft:iron_ingot", 0.7)
    add("minecraft:gold_ore", "minecraft:gold_ingot", 1.0)
    add("minecraft:diamond_ore", "minecraft:diamond", 1.0)
    add("minecraft:sand", "minecraft:glass", 0.1)
    add("minecraft:porkchop", "minecraft:cooked_porkchop", 0.35)
    add("minecraft:beef", "minecraft:cooked_beef", 0.35)
    add("minecraft:chicken", "minecraft:cooked_chicken", 0.35)
    add("minecraft:rabbit", "minecraft:cooked_rabbit", 0.35)
    add("minecraft:mutton", "minecraft:cooked_mutton", 0.35)
    add("minecraft:cobblestone", "minecraft:stone", 0.1)
    add("minecraft:stonebrick", "minecraft:stonebrick", 0.1,
        input_meta=0, output_meta=2)
    add("minecraft:clay_ball", "minecraft:brick", 0.3)
    add("minecraft:clay", "minecraft:hardened_clay", 0.35)
    add("minecraft:cactus", "minecraft:dye", 0.2, output_meta=13)
    add("minecraft:log", "minecraft:coal", 0.15, output_meta=1)
    add("minecraft:log2", "minecraft:coal", 0.15, output_meta=1)
    add("minecraft:emerald_ore", "minecraft:emerald", 1.0)
    add("minecraft:potato", "minecraft:baked_potato", 0.35)
    add("minecraft:netherrack", "minecraft:netherbrick", 0.1)
    add("minecraft:sponge", "minecraft:sponge", 0.15,
        input_meta=1, output_meta=0)
    add("minecraft:chorus_fruit", "minecraft:chorus_fruit_popped", 0.1)
    add("minecraft:fish", "minecraft:cooked_fish", 0.35, input_meta=0, output_meta=0)
    add("minecraft:fish", "minecraft:cooked_fish", 0.35, input_meta=1, output_meta=1)
    add("minecraft:coal_ore", "minecraft:coal", 0.1)
    add("minecraft:redstone_ore", "minecraft:redstone", 0.7)
    add("minecraft:lapis_ore", "minecraft:dye", 0.2, output_meta=4)
    add("minecraft:quartz_ore", "minecraft:quartz", 0.2)

    glazed = (
        "white", "orange", "magenta", "light_blue", "yellow", "lime",
        "pink", "gray", "light_gray", "cyan", "purple", "blue",
        "brown", "green", "red", "black",
    )
    for metadata, color in enumerate(glazed):
        add(
            "minecraft:stained_hardened_clay",
            f"minecraft:{color}_glazed_terracotta",
            0.1,
            input_meta=metadata,
        )

    return recipes


__all__ = ["register_vanilla_smelting_items", "register_vanilla_smelting_recipes"]
