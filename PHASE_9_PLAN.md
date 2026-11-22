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
- [x] Basic render-distance management and nearby chunk mesh streaming (5×5 around the player); frustum culling and asynchronous scheduling remain.
- [x] First-person player camera, mouse capture, fixed-tick WASD movement, gravity, jump, sprint, block raycast, mining, and block placement (temporary block palette).
- [ ] Visual HUD/crosshair/hotbar, real inventory interactions, world selection list, pause screen, and settings.
- [x] In-game F6 Python-only LAN host toggle and F7 join dialog (transport-level; no remote world replication yet).
- [ ] Audio, survival item drops/pickups, true item-backed hotbar, crafting/inventory screens, health/hunger display, pause/settings menus, and full in-game server/join UI.
- [x] User-facing Tk launcher entrypoint and Windows PyInstaller EXE build workflow.
- [ ] Windows build and real desktop smoke tests.

## Single-player implementation update

- [x] Launcher world-name and seed inputs.
- [x] Load existing Anvil/NBT world or create a new seeded world.
- [x] Save loaded chunks and world metadata when the game closes.
- [x] Player spawn is restored from the saved world spawn coordinates.
- [x] Player collision-based movement, gravity, jump, sprint, and camera follow.
- [x] Left-click block mining and right-click block placement.
- [x] Number keys 1–9 select a temporary development block palette.
- [x] 5×5 nearby chunk mesh streaming as the player crosses chunk boundaries.

## Status

Phase 9 remains **in progress**, not complete. The game now has a first playable interaction loop, but it is not yet a complete Minecraft-style single-player Survival experience. The temporary block palette bypasses the inventory; mining does not produce drops; there is no rendered HUD, proper inventory/hotbar UI, crafting screen, health/hunger presentation, mobs, audio, texture atlas, pause/settings menu, or full save-selection menu. Windows workflow success does not prove a real GPU launch; desktop smoke testing remains outstanding.
