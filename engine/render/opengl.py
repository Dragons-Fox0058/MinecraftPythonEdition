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


@dataclass
class _GPUChunk:
    vao: int
    vertex_buffer: int
    index_buffer: int
    index_count: int


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

    def render(self, mvp: np.ndarray, *, clear_color=(0.52, 0.72, 0.92, 1.0)) -> None:
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
        self.glfw.swap_buffers(self.window)
        self.glfw.poll_events()

    def should_close(self) -> bool:
        return self.window is None or bool(self.glfw.window_should_close(self.window))

    def close(self) -> None:
        if getattr(self, "gl", None) is not None:
            for key in tuple(getattr(self, "_chunks", {})):
                self.remove_chunk(key)
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
