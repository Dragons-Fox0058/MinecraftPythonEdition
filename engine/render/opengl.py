"""Optional GLFW + PyOpenGL renderer for indexed chunk meshes.

The module imports no graphical dependencies until a renderer is constructed,
so headless tests and server-side tools can import the engine safely.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import numpy as np

from engine.render.mesh import MeshData


_VERTEX_SHADER = """#version 330 core
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec3 in_color;
uniform mat4 u_mvp;
out vec3 vertex_color;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    vertex_color = in_color;
}
"""

_FRAGMENT_SHADER = """#version 330 core
in vec3 vertex_color;
out vec4 out_color;
void main() {
    out_color = vec4(vertex_color, 1.0);
}
"""


_HUD_VERTEX_SHADER = """#version 330 core
layout (location = 0) in vec2 in_position;
layout (location = 1) in vec3 in_color;
out vec3 vertex_color;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    vertex_color = in_color;
}
"""

_HUD_FRAGMENT_SHADER = """#version 330 core
in vec3 vertex_color;
out vec4 out_color;
void main() {
    out_color = vec4(vertex_color, 1.0);
}
"""


@dataclass
class _GPUChunk:
    vao: int
    vertex_buffer: int
    index_buffer: int
    index_count: int


_FONT_5X7 = {
    "A": ("01110","10001","10001","11111","10001","10001","10001"),
    "B": ("11110","10001","10001","11110","10001","10001","11110"),
    "C": ("01111","10000","10000","10000","10000","10000","01111"),
    "D": ("11110","10001","10001","10001","10001","10001","11110"),
    "E": ("11111","10000","10000","11110","10000","10000","11111"),
    "F": ("11111","10000","10000","11110","10000","10000","10000"),
    "G": ("01111","10000","10000","10111","10001","10001","01111"),
    "H": ("10001","10001","10001","11111","10001","10001","10001"),
    "I": ("11111","00100","00100","00100","00100","00100","11111"),
    "J": ("00111","00010","00010","00010","10010","10010","01100"),
    "K": ("10001","10010","10100","11000","10100","10010","10001"),
    "L": ("10000","10000","10000","10000","10000","10000","11111"),
    "M": ("10001","11011","10101","10101","10001","10001","10001"),
    "N": ("10001","11001","10101","10011","10001","10001","10001"),
    "O": ("01110","10001","10001","10001","10001","10001","01110"),
    "P": ("11110","10001","10001","11110","10000","10000","10000"),
    "Q": ("01110","10001","10001","10001","10101","10010","01101"),
    "R": ("11110","10001","10001","11110","10100","10010","10001"),
    "S": ("01111","10000","10000","01110","00001","00001","11110"),
    "T": ("11111","00100","00100","00100","00100","00100","00100"),
    "U": ("10001","10001","10001","10001","10001","10001","01110"),
    "V": ("10001","10001","10001","10001","10001","01010","00100"),
    "W": ("10001","10001","10001","10101","10101","10101","01010"),
    "X": ("10001","10001","01010","00100","01010","10001","10001"),
    "Y": ("10001","10001","01010","00100","00100","00100","00100"),
    "Z": ("11111","00001","00010","00100","01000","10000","11111"),
    "0": ("01110","10001","10011","10101","11001","10001","01110"),
    "1": ("00100","01100","00100","00100","00100","00100","01110"),
    "2": ("01110","10001","00001","00010","00100","01000","11111"),
    "3": ("11110","00001","00001","01110","00001","00001","11110"),
    "4": ("00010","00110","01010","10010","11111","00010","00010"),
    "5": ("11111","10000","10000","11110","00001","00001","11110"),
    "6": ("01110","10000","10000","11110","10001","10001","01110"),
    "7": ("11111","00001","00010","00100","01000","01000","01000"),
    "8": ("01110","10001","10001","01110","10001","10001","01110"),
    "9": ("01110","10001","10001","01111","00001","00001","01110"),
    ":": ("00000","00100","00100","00000","00100","00100","00000"),
    "-": ("00000","00000","00000","11111","00000","00000","00000"),
    ".": ("00000","00000","00000","00000","00000","00110","00110"),
    "/": ("00001","00010","00010","00100","01000","01000","10000"),
};

class OpenGLRenderer:
    """Own a GLFW window and GPU buffers for chunk meshes."""

    def __init__(self, width: int = 1280, height: int = 720,
                 title: str = "Minecraft Python Edition", *,
                 glfw_module=None, gl_module=None):
        if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
            raise ValueError("width must be a positive integer")
        if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
            raise ValueError("height must be a positive integer")
        if not isinstance(title, str) or not title:
            raise ValueError("title must not be empty")
        if glfw_module is None:
            try:
                import glfw as glfw_module
            except ImportError as exc:
                raise RuntimeError("install glfw to use the desktop renderer") from exc
        if gl_module is None:
            try:
                from OpenGL import GL as gl_module
            except ImportError as exc:
                raise RuntimeError("install PyOpenGL to use the desktop renderer") from exc
        self.glfw = glfw_module
        self.gl = gl_module
        self.window = None
        self.program = 0
        self._chunks: dict[object, _GPUChunk] = {}
        if not self.glfw.init():
            raise RuntimeError("GLFW initialization failed")
        try:
            self.glfw.window_hint(self.glfw.CONTEXT_VERSION_MAJOR, 3)
            self.glfw.window_hint(self.glfw.CONTEXT_VERSION_MINOR, 3)
            self.glfw.window_hint(self.glfw.OPENGL_PROFILE, self.glfw.OPENGL_CORE_PROFILE)
            self.window = self.glfw.create_window(width, height, title, None, None)
            if not self.window:
                raise RuntimeError("could not create an OpenGL 3.3 window")
            self.glfw.make_context_current(self.window)
            self.glfw.swap_interval(1)
            self.gl.glViewport(0, 0, width, height)
            self.gl.glEnable(self.gl.GL_DEPTH_TEST)
            self.gl.glEnable(self.gl.GL_CULL_FACE)
            self.gl.glCullFace(self.gl.GL_BACK)
            self.program = self._create_program(_VERTEX_SHADER, _FRAGMENT_SHADER)
            self._mvp_location = self.gl.glGetUniformLocation(self.program, "u_mvp")
            self.hud_program = self._create_program(_HUD_VERTEX_SHADER, _HUD_FRAGMENT_SHADER)
            self._hud_vao = int(self.gl.glGenVertexArrays(1))
            self._hud_buffer = int(self.gl.glGenBuffers(1))
            self.gl.glBindVertexArray(self._hud_vao)
            self.gl.glBindBuffer(self.gl.GL_ARRAY_BUFFER, self._hud_buffer)
            self.gl.glBufferData(self.gl.GL_ARRAY_BUFFER, 0, None, self.gl.GL_DYNAMIC_DRAW)
            hud_stride = 5 * np.dtype(np.float32).itemsize
            self.gl.glEnableVertexAttribArray(0)
            self.gl.glVertexAttribPointer(0, 2, self.gl.GL_FLOAT, self.gl.GL_FALSE, hud_stride, ctypes.c_void_p(0))
            self.gl.glEnableVertexAttribArray(1)
            self.gl.glVertexAttribPointer(1, 3, self.gl.GL_FLOAT, self.gl.GL_FALSE, hud_stride, ctypes.c_void_p(2 * np.dtype(np.float32).itemsize))
            self.gl.glBindVertexArray(0)
        except Exception:
            self.close()
            raise

    def _compile_shader(self, source: str, shader_type: int) -> int:
        gl = self.gl
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
            log = gl.glGetShaderInfoLog(shader)
            gl.glDeleteShader(shader)
            if isinstance(log, bytes):
                log = log.decode("utf-8", "replace")
            raise RuntimeError(f"OpenGL shader compilation failed: {log}")
        return shader

    def _create_program(self, vertex_source: str, fragment_source: str) -> int:
        gl = self.gl
        vertex = self._compile_shader(vertex_source, gl.GL_VERTEX_SHADER)
        fragment = self._compile_shader(fragment_source, gl.GL_FRAGMENT_SHADER)
        program = gl.glCreateProgram()
        try:
            gl.glAttachShader(program, vertex)
            gl.glAttachShader(program, fragment)
            gl.glLinkProgram(program)
            if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
                log = gl.glGetProgramInfoLog(program)
                if isinstance(log, bytes):
                    log = log.decode("utf-8", "replace")
                raise RuntimeError(f"OpenGL shader link failed: {log}")
            return program
        except Exception:
            gl.glDeleteProgram(program)
            raise
        finally:
            gl.glDeleteShader(vertex)
            gl.glDeleteShader(fragment)

    def upload_chunk_mesh(self, key, mesh: MeshData) -> None:
        if not isinstance(mesh, MeshData):
            raise TypeError("mesh must be MeshData")
        self.remove_chunk(key)
        if mesh.is_empty:
            return
        positions = np.asarray(mesh.positions, dtype=np.float32)
        colors = np.asarray(mesh.colors, dtype=np.float32)
        indices = np.asarray(mesh.indices, dtype=np.uint32)
        if positions.ndim != 2 or positions.shape[1] != 3 or colors.shape != positions.shape:
            raise ValueError("mesh positions and colors must both have shape (N, 3)")
        if indices.ndim != 1 or (indices.size and int(indices.max()) >= len(positions)):
            raise ValueError("mesh indices are invalid")
        interleaved = np.ascontiguousarray(np.concatenate((positions, colors), axis=1))
        gl = self.gl
        vao = int(gl.glGenVertexArrays(1))
        vertex_buffer = int(gl.glGenBuffers(1))
        index_buffer = int(gl.glGenBuffers(1))
        try:
            gl.glBindVertexArray(vao)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, gl.GL_STATIC_DRAW)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
            stride = 6 * np.dtype(np.float32).itemsize
            gl.glEnableVertexAttribArray(0)
            gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))
            gl.glEnableVertexAttribArray(1)
            gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, stride,
                                     ctypes.c_void_p(3 * np.dtype(np.float32).itemsize))
            gl.glBindVertexArray(0)
        except Exception:
            gl.glDeleteBuffers(1, [vertex_buffer, index_buffer])
            gl.glDeleteVertexArrays(1, [vao])
            raise
        self._chunks[key] = _GPUChunk(vao, vertex_buffer, index_buffer, int(indices.size))

    def remove_chunk(self, key) -> None:
        gpu = self._chunks.pop(key, None)
        if gpu is None:
            return
        self.gl.glDeleteBuffers(1, [gpu.vertex_buffer, gpu.index_buffer])
        self.gl.glDeleteVertexArrays(1, [gpu.vao])

    @staticmethod
    def _hud_vertices(selected_slot: int, health: float, food: int, paused: bool = False, inventory_slots=None) -> np.ndarray:
        vertices = []

        def rect(x0, y0, x1, y1, color):
            r, g, b = color
            vertices.extend((
                (x0, y0, r, g, b), (x1, y0, r, g, b), (x1, y1, r, g, b),
                (x0, y0, r, g, b), (x1, y1, r, g, b), (x0, y1, r, g, b),
            ))

        def text_label(value, x, y, scale=0.004, color=(0.94, 0.95, 0.98)):
            """Append compact 5x7 bitmap text to the HUD triangle stream."""
            cursor_x = x
            for character in str(value).upper():
                glyph = _FONT_5X7.get(character)
                if glyph is None:
                    cursor_x += 6 * scale
                    continue
                for row_index, row_bits in enumerate(glyph):
                    for column_index, bit in enumerate(row_bits):
                        if bit == "1":
                            x0 = cursor_x + column_index * scale
                            y1 = y - row_index * scale
                            rect(x0, y1 - scale, x0 + scale * 0.88, y1, color)
                cursor_x += 6 * scale

        # Center crosshair.
        rect(-0.012, -0.0015, 0.012, 0.0015, (0.96, 0.96, 0.96))
        rect(-0.0015, -0.018, 0.0015, 0.018, (0.96, 0.96, 0.96))
        text_label("MINECRAFT PYTHON EDITION", -0.965, 0.955, 0.0038, (0.96, 0.97, 1.0))
        text_label("HEALTH", -0.88, -0.605, 0.0025, (1.0, 0.82, 0.82))
        text_label("FOOD", 0.72, -0.605, 0.0025, (1.0, 0.86, 0.70))

        # Nine-slot hotbar with a clear selected-slot frame.
        slot_w, gap = 0.075, 0.008
        total = 9 * slot_w + 8 * gap
        left = -total / 2
        for index in range(9):
            x0 = left + index * (slot_w + gap)
            x1 = x0 + slot_w
            border = (0.95, 0.72, 0.22) if index == selected_slot else (0.52, 0.55, 0.60)
            rect(x0, -0.91, x1, -0.72, border)
            rect(x0 + 0.006, -0.904, x1 - 0.006, -0.726, (0.12, 0.14, 0.18))

        # Health and hunger indicators as compact bars.
        rect(-0.88, -0.66, -0.88 + 0.16 * max(0.0, min(1.0, health / 20.0)), -0.635, (0.85, 0.12, 0.14))
        rect(0.72, -0.66, 0.72 + 0.16 * max(0, min(20, food)) / 20.0, -0.635, (0.78, 0.48, 0.16))
        if paused:
            rect(-0.34, -0.27, 0.34, 0.27, (0.08, 0.10, 0.14))
            rect(-0.18, 0.08, 0.18, 0.13, (0.22, 0.48, 0.72))
            rect(-0.18, -0.02, 0.18, 0.03, (0.34, 0.38, 0.45))
            rect(-0.18, -0.12, 0.18, -0.07, (0.34, 0.38, 0.45))
            text_label("GAME MENU", -0.14, 0.205, 0.006, (1.0, 1.0, 1.0))
            text_label("RESUME", -0.105, 0.125, 0.004, (1.0, 1.0, 1.0))
            text_label("OPTIONS", -0.105, 0.035, 0.004, (0.90, 0.92, 0.96))
            text_label("SAVE AND QUIT", -0.16, -0.065, 0.0035, (0.90, 0.92, 0.96))
        if inventory_slots is not None:
            rect(-0.43, -0.36, 0.43, 0.36, (0.10, 0.12, 0.16))
            text_label("INVENTORY", -0.12, 0.315, 0.005, (1.0, 1.0, 1.0))
            slot_w, slot_h, gap_x, gap_y = 0.075, 0.105, 0.012, 0.025
            grid_left, grid_top = -0.3915, 0.245
            for index, entry in enumerate(inventory_slots[:36]):
                row, col = divmod(index, 9)
                x0 = grid_left + col * (slot_w + gap_x)
                y1 = grid_top - row * (slot_h + gap_y)
                x1, y0 = x0 + slot_w, y1 - slot_h
                border = (0.95, 0.72, 0.22) if index == selected_slot else (0.48, 0.52, 0.58)
                rect(x0, y0, x1, y1, border)
                rect(x0 + 0.005, y0 + 0.005, x1 - 0.005, y1 - 0.005, (0.16, 0.18, 0.22))
                item_id, count = entry
                if item_id:
                    color_value = (int(item_id) * 0x45D9F3B) & 0xFFFFFFFF
                    color = (0.35 + ((color_value >> 16) & 0xFF) / 390.0,
                             0.35 + ((color_value >> 8) & 0xFF) / 390.0,
                             0.35 + (color_value & 0xFF) / 390.0)
                    rect(x0 + 0.018, y0 + 0.027, x1 - 0.018, y1 - 0.027, color)
                    rect(x0 + 0.012, y0 + 0.012, x0 + 0.012 + min(1.0, int(count) / 64.0) * 0.05, y0 + 0.018, (0.92, 0.92, 0.92))
        return np.asarray(vertices, dtype=np.float32)

    def render(self, mvp: np.ndarray, *, clear_color=(0.52, 0.72, 0.92, 1.0),
               hud_state: dict | None = None) -> None:
        matrix = np.asarray(mvp, dtype=np.float32)
        if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
            raise ValueError("mvp must be a finite 4x4 matrix")
        gl = self.gl
        gl.glClearColor(*clear_color)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glUseProgram(self.program)
        gl.glUniformMatrix4fv(self._mvp_location, 1, gl.GL_FALSE,
                              np.ascontiguousarray(matrix.T))
        for gpu in self._chunks.values():
            gl.glBindVertexArray(gpu.vao)
            gl.glDrawElements(gl.GL_TRIANGLES, gpu.index_count, gl.GL_UNSIGNED_INT, None)
        gl.glBindVertexArray(0)
        if hud_state is not None:
            selected = int(hud_state.get("selected_slot", 0))
            health = float(hud_state.get("health", 20.0))
            food = int(hud_state.get("food", 20))
            paused = bool(hud_state.get("paused", False))
            inventory_slots = hud_state.get("inventory_slots")
            if not 0 <= selected < 9:
                raise ValueError("selected hotbar slot must be in [0, 8]")
            hud = self._hud_vertices(selected, health, food, paused, inventory_slots)
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glDisable(gl.GL_CULL_FACE)
            gl.glUseProgram(self.hud_program)
            gl.glBindVertexArray(self._hud_vao)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self._hud_buffer)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, hud.nbytes, hud, gl.GL_DYNAMIC_DRAW)
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(hud))
            gl.glBindVertexArray(0)
            gl.glEnable(gl.GL_CULL_FACE)
            gl.glEnable(gl.GL_DEPTH_TEST)
        self.glfw.swap_buffers(self.window)
        self.glfw.poll_events()

    def should_close(self) -> bool:
        return self.window is None or bool(self.glfw.window_should_close(self.window))

    def close(self) -> None:
        if getattr(self, "gl", None) is not None:
            for key in tuple(getattr(self, "_chunks", {})):
                self.remove_chunk(key)
            if getattr(self, "_hud_buffer", 0):
                self.gl.glDeleteBuffers(1, [self._hud_buffer])
                self._hud_buffer = 0
            if getattr(self, "_hud_vao", 0):
                self.gl.glDeleteVertexArrays(1, [self._hud_vao])
                self._hud_vao = 0
            if getattr(self, "hud_program", 0):
                self.gl.glDeleteProgram(self.hud_program)
                self.hud_program = 0
            if getattr(self, "program", 0):
                self.gl.glDeleteProgram(self.program)
                self.program = 0
        if getattr(self, "window", None) is not None:
            self.glfw.destroy_window(self.window)
            self.window = None
        if getattr(self, "glfw", None) is not None:
            self.glfw.terminate()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


__all__ = ["OpenGLRenderer"]
