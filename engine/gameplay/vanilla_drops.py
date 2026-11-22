"""Source-backed block drops for the supported Minecraft Java 1.12.2 subset.

Unknown blocks intentionally produce no drops. The resolver models BlockOre's
Fortune multiplier and the special vanilla ore item/count rules.
"""
from __future__ import annotations

import random
from collections.abc import Mapping

from engine.gameplay.items import Item, ItemStack


_SAME_ID_DROPS = frozenset({
    "dirt", "cobblestone", "planks", "sand", "sandstone", "obsidian",
    "log", "log2", "sapling", "dandelion", "poppy", "brown_mushroom",
    "red_mushroom", "pumpkin", "lit_pumpkin", "melon_block",
})


def _fortune_multiplier(rng, fortune: int) -> int:
    """Block.quantityDroppedWithBonus from 1.12.2."""
    if fortune <= 0:
        return 1
    return max(0, rng.randrange(fortune + 2) - 1) + 1


def resolve_vanilla_block_drops(
    block,
    block_items: Mapping[int, Item],
    *,
    flint_item: Item | None = None,
    rng: random.Random | None = None,
    fortune: int = 0,
    silk_touch: bool = False,
) -> list[ItemStack]:
    """Resolve drops for registered 1.12.2 blocks.

    block_items maps legacy numeric item IDs to registered Item objects (it
    includes both placeable block-items and ordinary drops). Harvest eligibility
    is checked by BlockBreaking before this function is called.
    """
    if not isinstance(block_items, Mapping):
        raise TypeError("block_items must map legacy item IDs to Item values")
    if isinstance(fortune, bool) or not isinstance(fortune, int) or not 0 <= fortune <= 3:
        raise ValueError("fortune must be an integer from 0 to 3")
    if not isinstance(silk_touch, bool):
        raise TypeError("silk_touch must be a bool")
    if rng is None:
        rng = random.Random(0)
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange(stop)")

    name = getattr(block, "registry_name", None)
    block_id = getattr(block, "block_id", None)

    # Silk Touch takes precedence over Fortune for these blocks.
    if silk_touch and name in {
        "stone", "glass", "coal_ore", "iron_ore", "gold_ore",
        "lapis_ore", "diamond_ore", "redstone_ore", "lit_redstone_ore",
        "emerald_ore", "quartz_ore",
    }:
        item = block_items.get(block_id)
        return [ItemStack(item, 1)] if item is not None else []

    if name == "stone":
        drop_id, count, metadata = 4, 1, 0
    elif name == "grass":
        drop_id, count, metadata = 3, 1, 0
    elif name == "glass":
        return []
    elif name == "gravel":
        # BlockGravel: nextInt(10 - fortune * 3) == 0 drops flint.
        if rng.randrange(10 - fortune * 3) == 0:
            return [ItemStack(flint_item, 1)] if flint_item is not None else []
        drop_id, count, metadata = 13, 1, 0
    elif name == "tallgrass":
        # Tall grass has a 1-in-8 seed drop chance in 1.12.2.
        return [ItemStack(block_items[295], 1)] if rng.randrange(8) == 0 and 295 in block_items else []
    elif name == "deadbush":
        count = rng.randrange(3)
        return [ItemStack(block_items[280], count)] if count and 280 in block_items else []
    elif name in ("leaves", "leaves2"):
        # Leaves use Fortune to improve the sapling drop probability.
        chance = max(1, 20 - fortune * 2)
        return [ItemStack(block_items[6], 1)] if rng.randrange(chance) == 0 and 6 in block_items else []
    elif name == "clay":
        return [ItemStack(block_items[337], 4)] if 337 in block_items else []
    elif name == "snow_layer":
        return [ItemStack(block_items[332], 1)] if 332 in block_items else []
    elif name == "snow":
        return [ItemStack(block_items[332], 4)] if 332 in block_items else []
    elif name == "glowstone":
        count = (2 + rng.randrange(3)) * _fortune_multiplier(rng, fortune)
        return [ItemStack(block_items[348], count)] if 348 in block_items else []
    elif name == "coal_ore":
        drop_id, count, metadata = 263, _fortune_multiplier(rng, fortune), 0
    elif name == "diamond_ore":
        drop_id, count, metadata = 264, _fortune_multiplier(rng, fortune), 0
    elif name == "emerald_ore":
        drop_id, count, metadata = 388, _fortune_multiplier(rng, fortune), 0
    elif name == "lapis_ore":
        drop_id = 351  # dye item; metadata 4 is lapis lazuli
        multiplier = _fortune_multiplier(rng, fortune)
        count = (4 + rng.randrange(5)) * multiplier
        metadata = 4
    elif name in ("redstone_ore", "lit_redstone_ore"):
        drop_id = 331
        multiplier = _fortune_multiplier(rng, fortune)
        count = (4 + rng.randrange(2)) * multiplier
        metadata = 0
    elif name == "quartz_ore":
        drop_id, count, metadata = 406, _fortune_multiplier(rng, fortune), 0
    elif name in ("iron_ore", "gold_ore"):
        # These ores drop themselves; Fortune does not multiply their block drop.
        drop_id, count, metadata = block_id, 1, 0
    elif name in _SAME_ID_DROPS:
        drop_id, count, metadata = block_id, 1, 0
    else:
        return []

    item = block_items.get(drop_id)
    if item is None:
        return []
    return [ItemStack(item, count, metadata=metadata)]


__all__ = ["resolve_vanilla_block_drops"]
