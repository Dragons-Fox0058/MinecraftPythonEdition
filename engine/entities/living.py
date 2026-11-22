"""engine.entities.living — EntityLivingBase with health and jumping."""
from __future__ import annotations
from engine.entities.entity import Entity
from engine.core import Vec3d

JUMP_VELOCITY = 0.42


class EntityLivingBase(Entity):
    def __init__(self, world, x=0.0, y=0.0, z=0.0):
        super().__init__(world, x, y, z)
        self.max_health = 20.0
        self.health = self.max_health
        self.hurt_time = 0
        self.death_time = 0
        self.jump_cooldown = 0

    def jump(self):
        if self.on_ground and self.jump_cooldown == 0:
            self.motion = Vec3d(self.motion.x, JUMP_VELOCITY, self.motion.z)
            self.on_ground = False
            self.jump_cooldown = 10

    def damage(self, amount):
        if self.hurt_time > 0:
            return
        self.health -= amount
        self.hurt_time = 10
        if self.health <= 0:
            self.health = 0
            self.dead = True

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def on_update(self):
        if self.hurt_time > 0:
            self.hurt_time -= 1
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
        super().on_update()
