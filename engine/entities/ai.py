"""Task scheduler and basic mob AI goals."""
from __future__ import annotations

import random

from engine.core import BlockPos, Vec3d


class AITask:
    """Base goal with an explicit start/update/continue/reset lifecycle."""
    def should_execute(self, mob):
        return True

    def should_continue(self, mob):
        return self.should_execute(mob)

    def start(self, mob):
        pass

    def update(self, mob):
        pass

    def reset(self, mob):
        pass


class AIWander(AITask):
    def __init__(self, speed=0.2, interval=40, rng=None):
        if speed <= 0 or interval <= 0:
            raise ValueError("speed and interval must be positive")
        self.speed = float(speed)
        self.interval = int(interval)
        self.target = None
        self.counter = 0
        self.rng = rng if rng is not None else random.Random()

    def should_execute(self, mob):
        if self.counter > 0:
            self.counter -= 1
        return self.counter <= 0 and self.target is None

    def should_continue(self, mob):
        return self.target is not None

    def start(self, mob):
        self.target = BlockPos(
            int(mob.pos.x + self.rng.uniform(-8, 8)),
            int(mob.pos.y),
            int(mob.pos.z + self.rng.uniform(-8, 8)),
        )
        self.counter = self.interval

    def update(self, mob):
        if self.target is None:
            return
        dx = self.target.x + 0.5 - mob.pos.x
        dz = self.target.z + 0.5 - mob.pos.z
        distance = (dx * dx + dz * dz) ** 0.5
        if distance < 1.0:
            self.target = None
            return
        mob.motion = Vec3d(
            mob.motion.x + (dx / distance) * self.speed * 0.1,
            mob.motion.y,
            mob.motion.z + (dz / distance) * self.speed * 0.1,
        )

    def reset(self, mob):
        self.target = None


class AILookAtPlayer(AITask):
    def __init__(self, range_=8):
        if range_ <= 0:
            raise ValueError("range must be positive")
        self.range = float(range_)

    def should_execute(self, mob):
        for entity in getattr(mob.world, "entities", ()):
            if getattr(entity, "name", None) == "Player":
                dx = entity.pos.x - mob.pos.x
                dz = entity.pos.z - mob.pos.z
                if dx * dx + dz * dz <= self.range * self.range:
                    return True
        return False


class EntityAITasks:
    """Runs each goal once per tick and preserves active goal state."""
    def __init__(self):
        self.tasks = []
        self._running = set()

    def add(self, task):
        if not isinstance(task, AITask):
            raise TypeError("task must be an AITask")
        if task in self.tasks:
            raise ValueError("task is already registered")
        self.tasks.append(task)

    def on_update(self, mob):
        for task in tuple(self.tasks):
            if task in self._running:
                if task.should_continue(mob):
                    task.update(mob)
                else:
                    task.reset(mob)
                    self._running.remove(task)
                continue
            if task.should_execute(mob):
                task.start(mob)
                self._running.add(task)
                task.update(mob)

    def is_running(self, task):
        return task in self._running
