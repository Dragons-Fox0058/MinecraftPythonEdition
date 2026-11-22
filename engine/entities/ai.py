"""engine.entities.ai — Lightweight task-based AI."""
from __future__ import annotations
from engine.core import BlockPos, Vec3d


class AITask:
    def should_execute(self, mob): return True
    def start(self, mob): pass
    def update(self, mob): pass
    def reset(self, mob): pass


class AIWander(AITask):
    def __init__(self, speed=0.2, interval=40):
        self.speed = speed; self.interval = interval
        self.target = None; self.counter = 0
    def should_execute(self, mob): return self.counter <= 0
    def start(self, mob):
        import random
        self.target = BlockPos(int(mob.pos.x + random.uniform(-8, 8)), int(mob.pos.y), int(mob.pos.z + random.uniform(-8, 8)))
        self.counter = self.interval
    def update(self, mob):
        if self.target is None:
            self.counter = 0; return
        dx = self.target.x + 0.5 - mob.pos.x
        dz = self.target.z + 0.5 - mob.pos.z
        d = (dx*dx + dz*dz) ** 0.5
        if d < 1.0:
            self.target = None; return
        mob.motion = Vec3d(mob.motion.x + (dx/d) * self.speed * 0.1, mob.motion.y, mob.motion.z + (dz/d) * self.speed * 0.1)
    def reset(self, mob):
        self.target = None


class AILookAtPlayer(AITask):
    def __init__(self, range_=8): self.range = range_
    def should_execute(self, mob):
        for e in mob.world.entities:
            if getattr(e, 'name', None) == 'Player':
                dx = e.pos.x - mob.pos.x; dz = e.pos.z - mob.pos.z
                if dx*dx + dz*dz <= self.range * self.range: return True
        return False


class EntityAITasks:
    def __init__(self):
        self.tasks = []
    def add(self, task): self.tasks.append(task)
    def on_update(self, mob):
        for t in list(self.tasks):
            if t.should_execute(mob):
                t.start(mob); t.update(mob); t.reset(mob)
