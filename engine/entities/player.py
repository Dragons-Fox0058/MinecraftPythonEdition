"""engine.entities.player — EntityPlayer with walking/sprinting."""
from __future__ import annotations
import math
from engine.entities.living import EntityLivingBase
from engine.core import Vec3d

WALK_SPEED = 0.1
SPRINT_SPEED = 0.13
SNEAK_SPEED = 0.03


class EntityPlayer(EntityLivingBase):
    def __init__(self, world, x=0.0, y=0.0, z=0.0, name='Player'):
        super().__init__(world, x, y, z)
        self.name = name
        self.set_size(0.6, 1.8)
        self.sprinting = False
        self.sneaking = False
        self.yaw = 0.0
        self.pitch = 0.0

    def get_move_speed(self):
        if self.sneaking:
            return SNEAK_SPEED
        if self.sprinting:
            return SPRINT_SPEED
        return WALK_SPEED

    def move_input(self, forward, strafe):
        speed = self.get_move_speed()
        yaw_rad = self.yaw * math.pi / 180.0
        sin_y = -math.sin(yaw_rad)
        cos_y = math.cos(yaw_rad)
        mx = strafe * cos_y - forward * sin_y
        mz = forward * cos_y - strafe * sin_y
        self.motion = Vec3d(self.motion.x + mx * speed, self.motion.y, self.motion.z + mz * speed)
