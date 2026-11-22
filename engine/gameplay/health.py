"""Player hunger, exhaustion, natural regeneration, and starvation."""
from __future__ import annotations

import math


class HungerManager:
    """Minecraft-style food and saturation state for a living player."""

    def __init__(self, food_level: int = 20, saturation: float = 5.0) -> None:
        if isinstance(food_level, bool) or not isinstance(food_level, int) or not 0 <= food_level <= 20:
            raise ValueError("food_level must be an integer from 0 to 20")
        if isinstance(saturation, bool) or not isinstance(saturation, (int, float)) or not math.isfinite(saturation) or saturation < 0:
            raise ValueError("saturation must be a non-negative number")
        self.food_level = food_level
        self.saturation = min(float(saturation), float(food_level))
        self.exhaustion = 0.0
        self.food_timer = 0
        self.tick_count = 0

    def add_exhaustion(self, amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
            raise ValueError("exhaustion must be a non-negative number")
        self.exhaustion = min(40.0, self.exhaustion + float(amount))

    def eat(self, food_points: int, saturation_modifier: float) -> None:
        if isinstance(food_points, bool) or not isinstance(food_points, int) or food_points < 0:
            raise ValueError("food_points must be a non-negative integer")
        if (isinstance(saturation_modifier, bool)
                or not isinstance(saturation_modifier, (int, float))
                or not math.isfinite(saturation_modifier) or saturation_modifier < 0):
            raise ValueError("saturation_modifier must be a non-negative number")
        self.food_level = min(20, self.food_level + food_points)
        self.saturation = min(
            float(self.food_level),
            self.saturation + food_points * float(saturation_modifier) * 2.0,
        )

    def _process_exhaustion(self) -> None:
        while self.exhaustion > 4.0:
            self.exhaustion -= 4.0
            if self.saturation > 0.0:
                self.saturation = max(0.0, self.saturation - 1.0)
            elif self.food_level > 0:
                self.food_level -= 1

    def tick(self, entity, natural_regeneration: bool = True,
             difficulty: str = "normal") -> None:
        """Advance one tick and apply healing/starvation to a living entity."""
        if difficulty not in ("peaceful", "easy", "normal", "hard"):
            raise ValueError("difficulty must be peaceful, easy, normal, or hard")
        if not hasattr(entity, "health") or not hasattr(entity, "max_health"):
            raise TypeError("entity must expose health and max_health")
        self.tick_count += 1
        self._process_exhaustion()

        if natural_regeneration and self.food_level >= 18 and entity.health < entity.max_health:
            interval = 10 if self.saturation > 0.0 else 80
            self.food_timer += 1
            if self.food_timer >= interval:
                entity.heal(1.0)
                self.add_exhaustion(6.0)
                self.food_timer = 0
        elif self.food_level == 0:
            self.food_timer += 1
            if self.food_timer >= 80:
                lower_bound = {
                    "peaceful": entity.max_health,
                    "easy": 10.0,
                    "normal": 1.0,
                    "hard": 0.0,
                }[difficulty]
                if difficulty != "peaceful" and entity.health > lower_bound:
                    entity.damage(1.0)
                self.food_timer = 0
        else:
            self.food_timer = 0

        self.saturation = min(self.saturation, float(self.food_level))


__all__ = ["HungerManager"]
