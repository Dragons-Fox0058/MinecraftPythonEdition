# Phase 9 — Rendering, input, and application

## Implemented foundations

- [x] Toolkit-neutral application configuration and lifecycle shell.
- [x] Fixed-timestep simulation loop with interpolation, bounded catch-up, and frame-time protection.
- [x] Backend-independent keyboard/mouse state, pressed/released edges, pointer deltas, scrolling, and focus-loss clearing.
- [x] CPU-side opaque chunk face extraction with adjacent-face culling and optional neighboring-chunk boundary culling.
- [x] Typed mesh buffers for positions, deterministic placeholder colors, and indexed triangles.
- [x] Optional GLFW/OpenGL 3.3 renderer with shader compilation, VAO/VBO/EBO upload, indexed drawing, and resource cleanup.
- [x] Unit tests for the loop, input state, empty/single/adjacent blocks, and chunk boundaries.

## Remaining implementation

- [x] GLFW window/context creation and platform lifecycle implemented; actual desktop smoke testing remains outstanding.
- [x] OpenGL GPU buffers, basic shaders, externally supplied MVP camera matrix, depth/cull state, and draw submission.
- [ ] Texture atlas and resource-pack loading; replace placeholder colors with 1.12.2 textures.
- [ ] Frustum culling, chunk render scheduling, dirty-mesh rebuilds, and render-distance management.
- [ ] Player camera, mouse capture, keyboard movement, block raycast, and interaction wiring.
- [ ] HUD, hotbar, inventory, menus, pause screen, and settings.
- [x] In-game F6 Python-only LAN host toggle and F7 join dialog (transport-level; no remote world replication yet).
- [ ] Audio, HUD, inventory, pause/settings menus, and full in-game server/join UI.
- [x] User-facing Tk launcher entrypoint and Windows PyInstaller EXE build workflow.
- [ ] Windows build and real desktop smoke tests.

## Status

Phase 9 is **in progress**. A first desktop preview now opens a GLFW/OpenGL 3.3 window, generates and meshes one overworld chunk, and supports free-camera movement. The launcher source and Windows EXE build workflow are present. Placeholder colors remain; textures, interaction, chunk streaming, HUD/inventory/menus, desktop smoke tests, and a verified EXE artifact remain outstanding.
