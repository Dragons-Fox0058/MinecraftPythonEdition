"""Tests for application timing, input state, and chunk meshing."""
import unittest
import numpy as np

from engine.app.runtime import GameConfig, FixedTimestepLoop, GameApplication
from engine.input.state import InputState
from engine.core import ChunkPos
from engine.world.chunk import Chunk
from engine.render.mesh import ChunkMeshBuilder


class TestFixedTimestepLoop(unittest.TestCase):
    def test_fixed_step_and_interpolation(self):
        loop = FixedTimestepLoop(20)
        steps = []
        count, alpha = loop.advance(0.125, steps.append)
        self.assertEqual(count, 2)
        self.assertAlmostEqual(alpha, 0.5)
        self.assertEqual(len(steps), 2)

    def test_catch_up_is_bounded_and_excess_time_is_dropped(self):
        loop = FixedTimestepLoop(20, max_frame_time=1.0, max_catch_up_ticks=2)
        count, _ = loop.advance(0.5, lambda dt: None)
        self.assertEqual(count, 2)
        self.assertGreater(loop.dropped_time, 0)

    def test_rejects_bad_elapsed(self):
        loop = FixedTimestepLoop()
        with self.assertRaises(ValueError):
            loop.advance(-1, lambda dt: None)

    def test_application_stops_when_event_pump_requests_it(self):
        rendered = []
        app = GameApplication(GameConfig(), lambda dt: None, rendered.append,
                              poll_events=lambda: len(rendered) < 2)
        times = iter((0.0, 0.0, 0.01, 0.01, 0.02, 0.02))
        app.run(clock=lambda: next(times), sleep=lambda _: None)
        self.assertEqual(len(rendered), 2)
        self.assertFalse(app.running)


class TestInputState(unittest.TestCase):
    def test_key_edges_and_held_state(self):
        state = InputState()
        state.key_down("W")
        state.key_down("W")
        self.assertTrue(state.is_key_down("W"))
        self.assertTrue(state.was_key_pressed("W"))
        state.begin_frame()
        self.assertFalse(state.was_key_pressed("W"))
        state.key_up("W")
        self.assertFalse(state.is_key_down("W"))
        self.assertTrue(state.was_key_released("W"))

    def test_mouse_delta_scroll_and_buttons(self):
        state = InputState()
        state.mouse_move(10, 20)
        state.mouse_move(13, 25)
        state.mouse_scroll(0, -1)
        state.button_down(1)
        self.assertEqual((state.mouse_dx, state.mouse_dy), (13, 25))
        self.assertEqual(state.scroll_y, -1)
        self.assertTrue(state.was_button_pressed(1))
        state.begin_frame()
        self.assertEqual((state.mouse_dx, state.mouse_dy), (0, 0))

    def test_focus_loss_clears_held_inputs(self):
        state = InputState()
        state.key_down("W")
        state.button_down(0)
        state.set_focus(False)
        self.assertFalse(state.is_key_down("W"))
        self.assertFalse(state.is_button_down(0))


class TestChunkMesh(unittest.TestCase):
    def test_empty_chunk_has_empty_mesh(self):
        mesh = ChunkMeshBuilder().build(Chunk(ChunkPos(0, 0)))
        self.assertTrue(mesh.is_empty)
        self.assertEqual(mesh.vertex_count, 0)

    def test_single_block_has_six_faces(self):
        chunk = Chunk(ChunkPos(0, 0))
        chunk.blocks[1, 2, 3] = 1
        mesh = ChunkMeshBuilder().build(chunk)
        self.assertEqual(mesh.vertex_count, 24)
        self.assertEqual(mesh.triangle_count, 12)
        self.assertEqual(mesh.positions.min(axis=0).tolist(), [1.0, 3.0, 2.0])
        self.assertEqual(mesh.positions.max(axis=0).tolist(), [2.0, 4.0, 3.0])

    def test_adjacent_blocks_hide_internal_face(self):
        chunk = Chunk(ChunkPos(0, 0))
        chunk.blocks[1, 2, 3] = 1
        chunk.blocks[2, 2, 3] = 1
        mesh = ChunkMeshBuilder().build(chunk)
        self.assertEqual(mesh.vertex_count, 40)
        self.assertEqual(mesh.triangle_count, 20)

    def test_neighbor_chunk_hides_shared_boundary_faces(self):
        chunk = Chunk(ChunkPos(0, 0))
        neighbor = Chunk(ChunkPos(1, 0))
        chunk.blocks[15, 1, 1] = 1
        neighbor.blocks[0, 1, 1] = 1
        mesh = ChunkMeshBuilder().build(chunk, neighbors={(1, 0): neighbor})
        self.assertEqual(mesh.vertex_count, 20)


if __name__ == "__main__":
    unittest.main()
