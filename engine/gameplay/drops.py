"""Dropped item entities and inventory pickup handling."""
from __future__ import annotations

from engine.entities.entity import Entity
from engine.gameplay.items import ItemStack


class EntityItem(Entity):
    """A world entity holding an ItemStack."""

    DEFAULT_PICKUP_DELAY = 10
    DEFAULT_LIFETIME = 6000

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

    def try_pickup(self, inventory) -> bool:
        if self.dead or self.pickup_delay > 0 or self.stack.is_empty:
            return False
        remainder = inventory.insert(self.stack)
        self.stack = remainder
        if self.stack.is_empty:
            self.kill()
            return True
        return False

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
