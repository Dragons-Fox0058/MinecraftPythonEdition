"""Minimal desktop world viewer built on the Phase 9 OpenGL foundations."""
from __future__ import annotations

import math
import time

from engine.input.state import InputState
from engine.render.camera import Camera
from engine.render.mesh import ChunkMeshBuilder
from engine.render.opengl import OpenGLRenderer
from engine.worldgen.generator import ChunkGeneratorOverworld


def main(*, seed: int = 0) -> None:
    """Open a first-person free-camera view of a generated overworld chunk.

    WASD moves, Space/Ctrl moves vertically, Shift accelerates, mouse looks,
    and Escape closes the window. Block interaction and texture assets are
    intentionally left for subsequent Phase 9 tasks.
    """
    try:
        import glfw
    except ImportError as exc:
        raise RuntimeError("Desktop mode requires glfw and PyOpenGL; install requirements.txt") from exc

    generator = ChunkGeneratorOverworld(int(seed))
    chunk = generator.generate_chunk(0, 0)
    mesh = ChunkMeshBuilder().build(chunk)
    camera = Camera(position=(8.0, 92.0, -12.0), yaw=0.0, pitch=28.0)
    input_state = InputState()

    with OpenGLRenderer(1280, 720) as renderer:
        window = renderer.window
        glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        def on_key(_window, key, _scancode, action, _mods):
            if action == glfw.PRESS:
                input_state.key_down(key)
                if key == glfw.KEY_ESCAPE:
                    glfw.set_window_should_close(window, True)
            elif action == glfw.RELEASE:
                input_state.key_up(key)

        def on_mouse(_window, x, y):
            if input_state.mouse_x == 0.0 and input_state.mouse_y == 0.0:
                input_state.mouse_x, input_state.mouse_y = x, y
                return
            input_state.mouse_move(x, y)

        glfw.set_key_callback(window, on_key)
        glfw.set_cursor_pos_callback(window, on_mouse)
        renderer.upload_chunk_mesh((0, 0), mesh)
        previous = time.perf_counter()
        while not renderer.should_close():
            now = time.perf_counter()
            dt = min(now - previous, 0.05)
            previous = now
            input_state.begin_frame()
            # GLFW callbacks update held keys; mouse deltas are consumed below.
            speed = 18.0 if input_state.is_key_down(glfw.KEY_LEFT_SHIFT) else 6.0
            right = float(input_state.is_key_down(glfw.KEY_D)) - float(input_state.is_key_down(glfw.KEY_A))
            forward = float(input_state.is_key_down(glfw.KEY_W)) - float(input_state.is_key_down(glfw.KEY_S))
            up = float(input_state.is_key_down(glfw.KEY_SPACE)) - float(input_state.is_key_down(glfw.KEY_LEFT_CONTROL))
            length = math.hypot(right, forward)
            if length > 0:
                right, forward = right / length, forward / length
            camera.move_local(right=right * speed * dt, up=up * speed * dt,
                              forward=forward * speed * dt)
            camera.rotate(-input_state.mouse_dx * 0.12, input_state.mouse_dy * 0.12)
            width, height = glfw.get_framebuffer_size(window)
            if width > 0 and height > 0:
                renderer.gl.glViewport(0, 0, width, height)
                renderer.render(camera.view_projection_matrix(width / height))
            input_state.begin_frame()


if __name__ == "__main__":
    main()
