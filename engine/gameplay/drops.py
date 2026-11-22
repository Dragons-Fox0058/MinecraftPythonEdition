"""Dropped item entities and inventory pickup handling."""
from __future__ import annotations

from engine.entities.entity import Entity
from engine.gameplay.items import ItemStack


class EntityItem(Entity):
    """A world entity holding an ItemStack."""

    DEFAULT_PICKUP_DELAY = 10
    DEFAULT_LIFETIME = 6000
    INFINITE_PICKUP_DELAY = 32767

    def __init__(self, world, x: float, y: float, z: float, stack: ItemStack,
                 pickup_delay: int = DEFAULT_PICKUP_DELAY,
                 lifetime: int = DEFAULT_LIFETIME) -> None:
        if not isinstance(stack, ItemStack):
            raise TypeError("stack must be an ItemStack")
        if stack.is_empty:
            raise ValueError("cannot spawn an empty item entity")
        if isinstance(pickup_delay, bool) or not isinstance(pickup_delay, int) or pickup_delay < 0:
            raise ValueError("pickup_delay must be a non-negative integer")
        if isinstance(lifetime, bool) or not isinstance(lifetime, int) or lifetime <= 0:
            raise ValueError("lifetime must be a positive integer")
        super().__init__(world, x, y, z)
        self.set_size(0.25, 0.25)
        self.stack = stack.copy()
        self.pickup_delay = pickup_delay
        self.lifetime = lifetime
        self.age = 0

    def on_update(self) -> None:
        if self.dead:
            return
        if self.pickup_delay > 0:
            self.pickup_delay -= 1
        self.age += 1
        super().on_update()
        if self.age >= self.lifetime:
            self.kill()
            return
        if self.ticks_existed % 25 == 0:
            self.search_for_nearby_items()

    def search_for_nearby_items(self) -> None:
        """Attempt vanilla-style merging with nearby live item entities."""
        for other in tuple(self.world.entities):
            if self.dead:
                break
            if not isinstance(other, EntityItem) or other is self or other.dead:
                continue
            if (abs(self.pos.x - other.pos.x) <= 0.75
                    and abs(self.pos.z - other.pos.z) <= 0.75
                    and abs(self.pos.y - other.pos.y) <= 0.5):
                self.try_merge(other)

    def try_merge(self, other: "EntityItem") -> bool:
        """Merge two compatible entities only when the complete stack fits."""
        if not isinstance(other, EntityItem) or other is self:
            return False
        if self.dead or other.dead:
            return False
        if (self.pickup_delay == self.INFINITE_PICKUP_DELAY
                or other.pickup_delay == self.INFINITE_PICKUP_DELAY):
            return False
        if not self.stack.can_stack_with(other.stack):
            return False
        if self.stack.count + other.stack.count > self.stack.item.max_stack_size:
            return False

        if self.stack.count >= other.stack.count:
            destination, source = self, other
        else:
            destination, source = other, self

        destination.stack.count += source.stack.count
        destination.pickup_delay = max(destination.pickup_delay, source.pickup_delay)
        destination.age = min(destination.age, source.age)
        source.kill()
        return True

    def try_pickup(self, inventory) -> bool:
        if self.dead or self.pickup_delay > 0 or self.stack.is_empty:
            return False
        original_count = self.stack.count
        remainder = inventory.insert(self.stack)
        self.stack = remainder
        if self.stack.is_empty:
            self.kill()
        return self.stack.count < original_count

    def kill(self) -> None:
        if self.dead:
            return
        super().kill()
        self.world.remove_entity(self)


class ItemDropManager:
    """Creates dropped item entities in a world's entity collection."""

    def __init__(self, world) -> None:
        self.world = world

    def spawn(self, x: float, y: float, z: float, stack: ItemStack,
              pickup_delay: int = EntityItem.DEFAULT_PICKUP_DELAY) -> EntityItem:
        entity = EntityItem(self.world, x, y, z, stack, pickup_delay=pickup_delay)
        self.world.add_entity(entity)
        return entity


__all__ = ["EntityItem", "ItemDropManager"]
