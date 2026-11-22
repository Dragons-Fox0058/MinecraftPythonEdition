"""Minecraft 1.12.2 item enchantment NBT helpers."""
from __future__ import annotations

from collections.abc import Mapping

ENCHANTMENT_IDS = {
    "protection": 0, "fire_protection": 1, "feather_falling": 2,
    "blast_protection": 3, "projectile_protection": 4, "respiration": 5,
    "aqua_affinity": 6, "thorns": 7, "depth_strider": 8,
    "frost_walker": 9, "binding_curse": 10, "sharpness": 16,
    "smite": 17, "bane_of_arthropods": 18, "knockback": 19,
    "fire_aspect": 20, "looting": 21, "sweeping": 22,
    "efficiency": 32, "silk_touch": 33, "unbreaking": 34,
    "fortune": 35, "power": 48, "punch": 49, "flame": 50,
    "infinity": 51, "luck_of_the_sea": 61, "lure": 62,
}


def _plain(value):
    if hasattr(value, "value"):
        return value.value
    return value


def _as_int(value):
    value = _plain(value)
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def get_enchantment_level(stack, enchantment: str | int) -> int:
    """Read enchantment level from vanilla 1.12.2 ItemStack NBT."""
    if stack is None or getattr(stack, "is_empty", True):
        return 0
    if isinstance(enchantment, str):
        key = enchantment.removeprefix("minecraft:")
        enchantment_id = ENCHANTMENT_IDS.get(key)
        if enchantment_id is None:
            raise ValueError(f"unknown enchantment: {enchantment}")
    elif isinstance(enchantment, int) and not isinstance(enchantment, bool) and enchantment >= 0:
        enchantment_id = enchantment
    else:
        raise TypeError("enchantment must be a known name or non-negative numeric ID")

    tag = getattr(stack, "nbt", None)
    if not isinstance(tag, Mapping):
        return 0
    highest = 0
    for list_name in ("ench", "StoredEnchantments"):
        entries = _plain(tag.get(list_name, ()))
        if hasattr(entries, "values"):
            entries = entries.values
        if not isinstance(entries, (list, tuple)):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            raw_id = _as_int(entry.get("id"))
            raw_level = _as_int(entry.get("lvl"))
            if raw_id == enchantment_id and raw_level is not None:
                highest = max(highest, min(255, max(0, raw_level)))
    return highest


def get_tool_enchantments(stack) -> tuple[int, bool]:
    """Return (Fortune level, Silk Touch enabled) from a held stack."""
    return get_enchantment_level(stack, "fortune"), get_enchantment_level(stack, "silk_touch") > 0


__all__ = ["ENCHANTMENT_IDS", "get_enchantment_level", "get_tool_enchantments"]
