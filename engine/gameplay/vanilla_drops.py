"""Small, source-backed vanilla 1.12.2 block-drop rules.

This intentionally covers only the starter desktop block catalogue. Unknown
blocks return no drops rather than receiving an incorrect same-ID item.
"""
from __future__ import annotations

import random
from collections.abc import Mapping

from engine.gameplay.items import Item, ItemStack


# Blocks whose normal drop is the corresponding block item.
_SAME_ID_DROPS = frozenset({
    "dirt", "cobblestone", "planks", "sand", "sandstone", "obsidian",
})


def resolve_vanilla_block_drops(
    block,
    block_items: Mapping[int, Item],
    *,
    flint_item: Item | None = None,
    rng: random.Random | None = None,
    fortune: int = 0,
    silk_touch: bool = False,
) -> list[ItemStack]:
    """Resolve drops for supported 1.12.2 blocks.

    Harvest eligibility is checked by BlockBreaking before this function is
    called. Fortune and Silk Touch are accepted for the small rules implemented
    here; callers must pass verified enchantment levels.
    """
    if not isinstance(block_items, Mapping):
        raise TypeError("block_items must map legacy block IDs to Item values")
    if isinstance(fortune, bool) or not isinstance(fortune, int) or not 0 <= fortune <= 3:
        raise ValueError("fortune must be an integer from 0 to 3")
    if not isinstance(silk_touch, bool):
        raise TypeError("silk_touch must be a bool")
    if rng is None:
        rng = random.Random(0)
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange(stop)")

    name = getattr(block, "registry_name", None)
    drop_item_id: int | None = None

    if name == "stone":
        drop_item_id = 4  # cobblestone, unless Silk Touch is used
        if silk_touch:
            drop_item_id = 1
    elif name == "grass":
        drop_item_id = 3  # dirt
    elif name == "glass":
        drop_item_id = 20 if silk_touch else None
    elif name == "gravel":
        # BlockGravel: nextInt(10 - fortune * 3) == 0
        bound = 10 - fortune * 3
        if rng.randrange(bound) == 0:
            if flint_item is None:
                return []
            return [ItemStack(flint_item, 1)]
        drop_item_id = 13
    elif name in _SAME_ID_DROPS:
        drop_item_id = getattr(block, "block_id", None)

    if drop_item_id is None:
        return []
    item = block_items.get(drop_item_id)
    return [ItemStack(item, 1)] if item is not None else []


__all__ = ["resolve_vanilla_block_drops"]
