"""Tests for first-person camera math."""
import unittest
import numpy as np

from engine.render.camera import Camera
from engine.render.opengl import OpenGLRenderer


class TestCamera(unittest.TestCase):
    def test_default_forward_points_positive_z(self):
        camera = Camera()
        np.testing.assert_allclose(camera.forward, (0, 0, 1), atol=1e-7)

    def test_yaw_and_pitch(self):
        camera = Camera()
        camera.rotate(90, 0)
        np.testing.assert_allclose(camera.forward, (-1, 0, 0), atol=1e-7)
        camera.rotate(-90, 30)
        self.assertAlmostEqual(camera.forward[1], -0.5, places=6)

    def test_pitch_is_clamped(self):
        camera = Camera(pitch=120)
        self.assertAlmostEqual(camera.pitch, 89.9)
        camera.rotate(0, -300)
        self.assertAlmostEqual(camera.pitch, -89.9)

    def test_local_movement(self):
        camera = Camera(position=(0, 0, 0))
        camera.move_local(right=2, up=1, forward=3)
        np.testing.assert_allclose(camera.position, (2, 1, 3), atol=1e-7)

    def test_hud_geometry_contains_crosshair_hotbar_and_status_bars(self):
        vertices = OpenGLRenderer._hud_vertices(4, 10.0, 15)
        self.assertEqual(vertices.ndim, 2)
        self.assertEqual(vertices.shape[1], 5)
        self.assertGreater(vertices.shape[0], 100)
        self.assertTrue(np.isfinite(vertices).all())

    def test_view_and_projection_matrices(self):
        camera = Camera(position=(1, 2, 3))
        view = camera.view_matrix()
        projection = camera.projection_matrix(16 / 9)
        combined = camera.view_projection_matrix(16 / 9)
        self.assertEqual(view.shape, (4, 4))
        self.assertEqual(projection.shape, (4, 4))
        self.assertEqual(combined.shape, (4, 4))
        self.assertTrue(np.isfinite(combined).all())
        with self.assertRaises(ValueError):
            camera.projection_matrix(0)


if __name__ == "__main__":
    unittest.main()
