"""engine.entities.entity — Entity base with vanilla 1.12.2 physics."""
from __future__ import annotations
from engine.core import Vec3d, AxisAlignedBB

GRAVITY = 0.08
AIR_DRAG = 0.98
TERMINAL_VELOCITY = -3.92
GROUND_FRICTION_DEFAULT = 0.6


class Entity:
    def __init__(self, world, x=0.0, y=0.0, z=0.0):
        self.world = world
        self.pos = Vec3d(x, y, z)
        self.motion = Vec3d(0.0, 0.0, 0.0)
        self.prev_pos = self.pos
        self.width = 0.6
        self.height = 1.8
        self.eye_height = 1.62
        self.on_ground = False
        self.collided_horizontally = False
        self.collided_vertically = False
        self.no_clip = False
        self.ticks_existed = 0
        self.dead = False
        self.fall_distance = 0.0
        self.step_height = 0.6

    def get_entity_bounding_box(self):
        half = self.width * 0.5
        return AxisAlignedBB(
            self.pos.x - half, self.pos.y, self.pos.z - half,
            self.pos.x + half, self.pos.y + self.height, self.pos.z + half,
        )

    def set_position(self, x, y, z):
        self.pos = Vec3d(x, y, z)

    def set_size(self, width, height):
        self.width = width
        self.height = height

    def move(self, mx, my, mz):
        if self.no_clip:
            self.pos = Vec3d(self.pos.x + mx, self.pos.y + my, self.pos.z + mz)
            return

        aabb = self.get_entity_bounding_box()
        input_mx, input_my, input_mz = mx, my, mz

        # 1) resolve Y first using the SWEPT box (original expanded by movement)
        swept = aabb.add_coord(mx, my, mz)
        boxes = self.world.get_collision_boxes(swept)
        for box in boxes:
            my = box.calculate_y_offset(aabb, my)
        aabb = aabb.offset(0, my, 0)

        # 2) resolve X
        for box in boxes:
            mx = box.calculate_x_offset(aabb, mx)
        aabb = aabb.offset(mx, 0, 0)

        # 3) resolve Z
        for box in boxes:
            mz = box.calculate_z_offset(aabb, mz)
        aabb = aabb.offset(0, 0, mz)

        # 4) state (vanilla Entity.move semantics)
        self.collided_vertically = (my != input_my)
        self.collided_horizontally = (mx != input_mx) or (mz != input_mz)
        self.on_ground = self.collided_vertically and input_my < 0
        if self.on_ground:
            self.fall_distance = 0.0
        elif input_my < 0:
            self.fall_distance += -input_my

        self.pos = Vec3d(
            aabb.min_x + self.width * 0.5,
            aabb.min_y,
            aabb.min_z + self.width * 0.5,
        )
        self.motion = Vec3d(mx, my, mz)

    def on_update(self):
        self.ticks_existed += 1
        self.prev_pos = self.pos

        # On the ground (or at rest), apply gravity before moving so the
        # collision check keeps the entity grounded.
        # While airborne, move with the current velocity first, then apply
        # gravity and drag. This preserves the vanilla-style jump impulse.
        if self.on_ground or self.motion.y == 0.0:
            self.motion = Vec3d(
                self.motion.x,
                self.motion.y - GRAVITY,
                self.motion.z,
            )
            self.move(self.motion.x, self.motion.y, self.motion.z)
        else:
            self.move(self.motion.x, self.motion.y, self.motion.z)
            self.motion = Vec3d(
                self.motion.x,
                self.motion.y - GRAVITY,
                self.motion.z,
            )

        # Air resistance
        self.motion = Vec3d(
            self.motion.x * AIR_DRAG,
            self.motion.y * AIR_DRAG,
            self.motion.z * AIR_DRAG,
        )

        if self.on_ground:
            f = self.get_ground_friction()
            self.motion = Vec3d(
                self.motion.x * f,
                self.motion.y,
                self.motion.z * f,
            )

        if self.motion.y < TERMINAL_VELOCITY:
            self.motion = Vec3d(
                self.motion.x,
                TERMINAL_VELOCITY,
                self.motion.z,
            )

    def get_ground_friction(self):
        return GROUND_FRICTION_DEFAULT

    def is_alive(self):
        return not self.dead

    def kill(self):
        self.dead = True

    def __repr__(self):
        return '%s(%.2f, %.2f, %.2f)' % (type(self).__name__, self.pos.x, self.pos.y, self.pos.z)
