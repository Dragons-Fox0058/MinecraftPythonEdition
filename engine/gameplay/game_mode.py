"""Java Edition 1.12.2 player game modes and command parsing."""
from __future__ import annotations

from enum import IntEnum


class GameMode(IntEnum):
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    SPECTATOR = 3

    @property
    def display_name(self) -> str:
        return {
            GameMode.SURVIVAL: "Survival",
            GameMode.CREATIVE: "Creative",
            GameMode.ADVENTURE: "Adventure",
            GameMode.SPECTATOR: "Spectator",
        }[self]

    @classmethod
    def parse(cls, value) -> "GameMode":
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            raise ValueError("invalid game mode")
        if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
            try:
                return cls(int(value))
            except ValueError as exc:
                raise ValueError(f"unknown game mode: {value}") from exc
        aliases = {
            "s": cls.SURVIVAL, "survival": cls.SURVIVAL,
            "c": cls.CREATIVE, "creative": cls.CREATIVE,
            "a": cls.ADVENTURE, "adventure": cls.ADVENTURE,
            "sp": cls.SPECTATOR, "spectator": cls.SPECTATOR,
        }
        try:
            return aliases[str(value).strip().lower()]
        except KeyError as exc:
            raise ValueError(f"unknown game mode: {value}") from exc


def _plain(value):
    return getattr(value, "value", value)


def _tag_values(value):
    value = _plain(value)
    values = getattr(value, "values", None)
    if values is not None:
        return tuple(_plain(item) for item in values)
    if isinstance(value, (list, tuple)):
        return tuple(_plain(item) for item in value)
    return ()


def stack_has_block_restriction(stack, tag_name: str, block_name: str) -> bool:
    """Match 1.12.2 CanDestroy/CanPlaceOn string entries."""
    if stack is None or getattr(stack, "is_empty", True):
        return False
    nbt = getattr(stack, "nbt", None)
    if not isinstance(nbt, dict):
        return False
    values = _tag_values(nbt.get(tag_name))
    target = str(block_name).removeprefix("minecraft:")
    return any(str(entry).removeprefix("minecraft:") in (target, "*") for entry in values)


__all__ = ["GameMode", "stack_has_block_restriction"]
