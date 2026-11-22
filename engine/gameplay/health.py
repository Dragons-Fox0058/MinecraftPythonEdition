"""Player hunger, food properties, exhaustion, regeneration, and starvation."""
from __future__ import annotations

import math

from engine.gameplay.items import Item, ItemStack


class FoodProperties:
    __slots__ = ("food_points", "saturation_modifier", "always_edible")

    def __init__(self, food_points: int, saturation_modifier: float,
                 always_edible: bool = False) -> None:
        if isinstance(food_points, bool) or not isinstance(food_points, int) or not 0 <= food_points <= 20:
            raise ValueError("food_points must be an integer from 0 to 20")
        if (isinstance(saturation_modifier, bool)
                or not isinstance(saturation_modifier, (int, float))
                or not math.isfinite(saturation_modifier) or saturation_modifier < 0):
            raise ValueError("saturation_modifier must be finite and non-negative")
        if not isinstance(always_edible, bool):
            raise ValueError("always_edible must be a bool")
        self.food_points = food_points
        self.saturation_modifier = float(saturation_modifier)
        self.always_edible = always_edible


class FoodRegistry:
    def __init__(self) -> None:
        self._foods: dict[tuple[Item, int | None], FoodProperties] = {}

    def register(self, item: Item, properties: FoodProperties,
                 metadata: int | None = None) -> None:
        if not isinstance(item, Item):
            raise TypeError("food item must be an Item")
        if not isinstance(properties, FoodProperties):
            raise TypeError("properties must be FoodProperties")
        if metadata is not None and (
            isinstance(metadata, bool) or not isinstance(metadata, int)
            or not 0 <= metadata <= 32767
        ):
            raise ValueError("metadata must be None or an integer from 0 to 32767")
        key = (item, metadata)
        if key in self._foods:
            raise ValueError(f"food already registered: {item.name} metadata={metadata}")
        self._foods[key] = properties

    def get(self, item: Item, metadata: int = 0) -> FoodProperties | None:
        return self._foods.get((item, metadata), self._foods.get((item, None)))

    def __len__(self) -> int:
        return len(self._foods)


class HungerManager:
    """Minecraft-style food and saturation state for a living player."""

    def __init__(self, food_level: int = 20, saturation: float = 5.0) -> None:
        if isinstance(food_level, bool) or not isinstance(food_level, int) or not 0 <= food_level <= 20:
            raise ValueError("food_level must be an integer from 0 to 20")
        if (isinstance(saturation, bool) or not isinstance(saturation, (int, float))
                or not math.isfinite(saturation) or saturation < 0):
            raise ValueError("saturation must be a finite non-negative number")
        self.food_level = food_level
        self.saturation = min(float(saturation), float(food_level))
        self.exhaustion = 0.0
        self.food_timer = 0
        self.tick_count = 0

    def can_eat(self, always_edible: bool = False) -> bool:
        if not isinstance(always_edible, bool):
            raise TypeError("always_edible must be a bool")
        return self.food_level < 20 or always_edible

    def add_exhaustion(self, amount: float) -> None:
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError("exhaustion must be finite and non-negative")
        self.exhaustion = min(40.0, self.exhaustion + float(amount))

    def eat(self, food_points: int, saturation_modifier: float) -> None:
        if isinstance(food_points, bool) or not isinstance(food_points, int) or food_points < 0:
            raise ValueError("food_points must be a non-negative integer")
        if (isinstance(saturation_modifier, bool)
                or not isinstance(saturation_modifier, (int, float))
                or not math.isfinite(saturation_modifier) or saturation_modifier < 0):
            raise ValueError("saturation_modifier must be finite and non-negative")
        self.food_level = min(20, self.food_level + food_points)
        self.saturation = min(
            float(self.food_level),
            self.saturation + food_points * float(saturation_modifier) * 2.0,
        )

    def consume(self, stack: ItemStack, foods: FoodRegistry) -> bool:
        """Consume one registered food item; return False if it cannot be eaten."""
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if not isinstance(foods, FoodRegistry):
            raise TypeError("foods must be a FoodRegistry")
        if stack.is_empty:
            return False
        properties = foods.get(stack.item, stack.metadata)
        if properties is None or not self.can_eat(properties.always_edible):
            return False
        self.eat(properties.food_points, properties.saturation_modifier)
        stack.shrink(1)
        return True

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
        if not isinstance(natural_regeneration, bool):
            raise TypeError("natural_regeneration must be a bool")
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


__all__ = ["FoodProperties", "FoodRegistry", "HungerManager"]
