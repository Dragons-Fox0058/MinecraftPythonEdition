# Phase 9 — Rendering, input, and application

## Implemented foundations

- [x] Toolkit-neutral application configuration and lifecycle shell.
- [x] Fixed-timestep simulation loop with interpolation, bounded catch-up, and frame-time protection.
- [x] Backend-independent keyboard/mouse state, pressed/released edges, pointer deltas, scrolling, and focus-loss clearing.
- [x] CPU-side opaque chunk face extraction with adjacent-face culling and optional neighboring-chunk boundary culling.
- [x] Typed mesh buffers for positions, deterministic placeholder colors, and indexed triangles.
- [x] Unit tests for the loop, input state, empty/single/adjacent blocks, and chunk boundaries.

## Remaining implementation

- [ ] Window/context creation and platform lifecycle (GLFW or equivalent).
- [ ] Actual OpenGL GPU buffers, shaders, camera matrices, depth/cull state, and draw submission.
- [ ] Texture atlas and resource-pack loading; replace placeholder colors with 1.12.2 textures.
- [ ] Frustum culling, chunk render scheduling, dirty-mesh rebuilds, and render-distance management.
- [ ] Player camera, mouse capture, keyboard movement, block raycast, and interaction wiring.
- [ ] HUD, hotbar, inventory, menus, pause screen, and settings.
- [ ] Audio and user-facing launcher/build pipeline.
- [ ] Windows build and real desktop smoke tests.

## Status

Phase 9 is **in progress**. The application, input, and CPU mesh foundations are testable without a graphical display. This is not yet a playable desktop client: there is no window/context backend, GPU renderer, texture atlas, or HUD.
