"""Minecraft-style first-person camera and OpenGL matrix helpers."""
from __future__ import annotations

import math
import numpy as np


class Camera:
    def __init__(self, position=(0.0, 64.0, 0.0), yaw: float = 0.0,
                 pitch: float = 0.0, fov_degrees: float = 70.0,
                 near: float = 0.05, far: float = 1024.0):
        self.position = np.asarray(position, dtype=np.float64)
        if self.position.shape != (3,) or not np.isfinite(self.position).all():
            raise ValueError("position must be a finite 3D vector")
        self.yaw = float(yaw)
        self.pitch = float(pitch)
        self.fov_degrees = float(fov_degrees)
        self.near = float(near)
        self.far = float(far)
        if not all(math.isfinite(v) for v in (self.yaw, self.pitch, self.fov_degrees, self.near, self.far)):
            raise ValueError("camera parameters must be finite")
        if not 1.0 <= self.fov_degrees < 179.0:
            raise ValueError("field of view must be between 1 and 179 degrees")
        if self.near <= 0 or self.far <= self.near:
            raise ValueError("camera planes must satisfy 0 < near < far")
        self.pitch = max(-89.9, min(89.9, self.pitch))

    @property
    def forward(self) -> np.ndarray:
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        cp = math.cos(pitch)
        return np.asarray((-math.sin(yaw) * cp, -math.sin(pitch),
                           math.cos(yaw) * cp), dtype=np.float64)

    @property
    def right(self) -> np.ndarray:
        value = np.cross(np.asarray((0.0, 1.0, 0.0)), self.forward)
        length = np.linalg.norm(value)
        return value / length if length else np.asarray((1.0, 0.0, 0.0))

    def rotate(self, delta_yaw: float, delta_pitch: float) -> None:
        if not math.isfinite(delta_yaw) or not math.isfinite(delta_pitch):
            raise ValueError("camera rotation must be finite")
        self.yaw = (self.yaw + delta_yaw) % 360.0
        self.pitch = max(-89.9, min(89.9, self.pitch + delta_pitch))

    def move_local(self, right: float = 0.0, up: float = 0.0,
                   forward: float = 0.0) -> None:
        values = (right, up, forward)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("movement must be finite")
        self.position += self.right * right
        self.position[1] += up
        self.position += self.forward * forward

    def view_matrix(self) -> np.ndarray:
        eye = self.position
        target = eye + self.forward
        up = np.asarray((0.0, 1.0, 0.0), dtype=np.float64)
        forward = target - eye
        forward /= np.linalg.norm(forward)
        side = np.cross(up, forward)
        side /= np.linalg.norm(side)
        camera_up = np.cross(forward, side)
        matrix = np.identity(4, dtype=np.float64)
        matrix[0, :3] = side
        matrix[1, :3] = camera_up
        matrix[2, :3] = -forward
        matrix[0, 3] = -np.dot(side, eye)
        matrix[1, 3] = -np.dot(camera_up, eye)
        matrix[2, 3] = np.dot(forward, eye)
        return matrix.astype(np.float32)

    def projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        if not math.isfinite(aspect_ratio) or aspect_ratio <= 0:
            raise ValueError("aspect_ratio must be finite and positive")
        f = 1.0 / math.tan(math.radians(self.fov_degrees) / 2.0)
        n, far = self.near, self.far
        matrix = np.zeros((4, 4), dtype=np.float64)
        matrix[0, 0] = f / aspect_ratio
        matrix[1, 1] = f
        matrix[2, 2] = (far + n) / (n - far)
        matrix[2, 3] = (2.0 * far * n) / (n - far)
        matrix[3, 2] = -1.0
        return matrix.astype(np.float32)

    def view_projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        return self.projection_matrix(aspect_ratio) @ self.view_matrix()

    def ray_direction(self) -> np.ndarray:
        return self.forward.copy()


__all__ = ["Camera"]
