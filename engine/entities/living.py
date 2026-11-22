"""engine.entities.living — EntityLivingBase with health and jumping."""
from __future__ import annotations
import math
from engine.entities.entity import Entity
from engine.core import Vec3d
from engine.gameplay.effects import StatusEffectManager

JUMP_VELOCITY = 0.42


class EntityLivingBase(Entity):
    def __init__(self, world, x=0.0, y=0.0, z=0.0):
        super().__init__(world, x, y, z)
        self.max_health = 20.0
        self.health = self.max_health
        self.hurt_time = 0
        self.max_hurt_resistant_time = 20
        self.hurt_resistant_time = 0
        self.last_damage = 0.0
        self.death_time = 0
        self.jump_cooldown = 0
        self.status_effects = StatusEffectManager()

    def jump(self):
        if self.on_ground and self.jump_cooldown == 0:
            self.motion = Vec3d(self.motion.x, JUMP_VELOCITY, self.motion.z)
            self.on_ground = False
            self.jump_cooldown = 10

    def damage(self, amount):
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError("damage amount must be finite and non-negative")
        if self.dead or amount == 0:
            return False

        # Vanilla's 20-tick hurt-resistance window rejects weaker hits but
        # permits a stronger hit to apply only the difference.
        applied = float(amount)
        if self.hurt_resistant_time > self.max_hurt_resistant_time // 2:
            if amount <= self.last_damage:
                return False
            applied = float(amount) - self.last_damage

        self.last_damage = float(amount)
        self.hurt_resistant_time = self.max_hurt_resistant_time
        self.hurt_time = self.max_hurt_resistant_time // 2
        self.health -= applied
        if self.health <= 0:
            self.health = 0
            self.dead = True
        return True

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def on_update(self):
        if self.hurt_time > 0:
            self.hurt_time -= 1
        if self.hurt_resistant_time > 0:
            self.hurt_resistant_time -= 1
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
        if not self.dead:
            self.status_effects.tick(self)
        super().on_update()
