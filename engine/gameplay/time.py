"""World clock and game-rule storage for the Minecraft 1.12.2 target."""
from __future__ import annotations


class GameRules:
    """Typed game-rule values with vanilla-style defaults."""

    DEFAULTS = {
        "doDaylightCycle": True,
        "announceAdvancements": True,
        "gameLoopFunction": "",
        "keepInventory": False,
        "doMobSpawning": True,
        "doMobLoot": True,
        "doEntityDrops": True,
        "doTileDrops": True,
        "doFireTick": True,
        "naturalRegeneration": True,
        "mobGriefing": True,
        "doWeatherCycle": True,
        "commandBlockOutput": True,
        "logAdminCommands": True,
        "showDeathMessages": True,
        "spectatorsGenerateChunks": True,
        "sendCommandFeedback": True,
        "reducedDebugInfo": False,
        "randomTickSpeed": 3,
        "maxEntityCramming": 24,
        "spawnRadius": 10,
        "disableElytraMovementCheck": False,
        "doLimitedCrafting": False,
        "maxCommandChainLength": 65536,
    }

    def __init__(self) -> None:
        self._rules = dict(self.DEFAULTS)

    def add_rule(self, name: str, default: bool | int | str) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("rule name must be a non-empty string")
        if name in self._rules:
            raise ValueError(f"game rule already exists: {name}")
        if isinstance(default, bool):
            self._rules[name] = default
        elif isinstance(default, int):
            self._rules[name] = default
        elif isinstance(default, str):
            self._rules[name] = default
        else:
            raise TypeError("game rule defaults must be bool, int, or str")

    def set(self, name: str, value: bool | int | str) -> None:
        if name not in self._rules:
            raise KeyError(f"unknown game rule: {name}")
        current = self._rules[name]
        if isinstance(current, str):
            if not isinstance(value, str):
                raise TypeError("this game rule requires a string")
        elif isinstance(current, bool):
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized not in ("true", "false"):
                    raise ValueError("boolean game rules accept true or false")
                value = normalized == "true"
            if not isinstance(value, bool):
                raise TypeError("this game rule requires a bool")
        else:
            if isinstance(value, str):
                try:
                    value = int(value.strip())
                except ValueError as exc:
                    raise ValueError("integer game rules require an integer") from exc
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("this game rule requires an int")
        self._rules[name] = value

    def get(self, name: str) -> bool | int | str:
        if name not in self._rules:
            raise KeyError(f"unknown game rule: {name}")
        return self._rules[name]

    def get_bool(self, name: str) -> bool:
        value = self.get(name)
        if not isinstance(value, bool):
            raise TypeError(f"game rule {name} is not boolean")
        return value

    def get_int(self, name: str) -> int:
        value = self.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"game rule {name} is not an integer")
        return value

    def get_str(self, name: str) -> str:
        value = self.get(name)
        if not isinstance(value, str):
            raise TypeError(f"game rule {name} is not a string")
        return value

    def names(self) -> tuple[str, ...]:
        return tuple(self._rules)


class WorldTime:
    """Tracks total world ticks and the independently pausable day clock."""

    DAY_LENGTH = 24000

    def __init__(self, total_time: int = 0, day_time: int = 6000) -> None:
        for label, value in (("total_time", total_time), ("day_time", day_time)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")
        self.total_time = total_time
        self.day_time = day_time

    @property
    def time_of_day(self) -> int:
        return self.day_time % self.DAY_LENGTH

    @property
    def day_count(self) -> int:
        return self.day_time // self.DAY_LENGTH

    @property
    def is_day(self) -> bool:
        return self.time_of_day < 12000

    def set_day_time(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("day time must be an integer")
        if value < 0:
            raise ValueError("day time cannot be negative")
        self.day_time = value

    def add_day_time(self, ticks: int) -> None:
        if isinstance(ticks, bool) or not isinstance(ticks, int):
            raise TypeError("ticks must be an integer")
        self.day_time = max(0, self.day_time + ticks)

    def tick(self, daylight_cycle: bool = True) -> None:
        if not isinstance(daylight_cycle, bool):
            raise TypeError("daylight_cycle must be a bool")
        self.total_time += 1
        if daylight_cycle:
            self.day_time += 1


__all__ = ["GameRules", "WorldTime"]
