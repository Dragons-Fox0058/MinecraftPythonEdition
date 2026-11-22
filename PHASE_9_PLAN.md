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
- [x] Built-in 5×7 bitmap font for visible Python Edition branding, HUD labels, inventory title, and pause-menu labels.
- [x] Pause-menu Q shortcut saves world/player data through the normal shutdown path.
- [x] Basic render-distance management and nearby chunk mesh streaming (5×5 around the player); frustum culling and asynchronous scheduling remain.
- [x] First-person player camera, mouse capture, fixed-tick WASD movement, gravity, jump, sprint, block raycast, mining, and block placement (temporary block palette).
- [x] Basic rendered crosshair, nine-slot hotbar frame, and health/hunger bars; item icons/count labels and full inventory screen remain.
- [x] In-game F6 Python-only LAN host toggle and F7 join dialog (transport-level; no remote world replication yet).
- [x] Basic block item drops, pickup into a 36-slot inventory, selected-stack placement, player health/hunger ticking, and player inventory NBT save/load for the supported block-item subset.\n- [ ] Full vanilla item/block catalogue, crafting UI, item icons/count text, complete food/combat/damage systems, audio, video/audio settings, and full in-game server/join UI.
- [x] User-facing Tk launcher entrypoint and Windows PyInstaller EXE build workflow.
- [ ] Windows build and real desktop smoke tests.

## Single-player implementation update

- [x] Launcher world-name and seed inputs, plus saved-world dropdown selection.
- [x] Load existing Anvil/NBT world or create a new seeded world.
- [x] Save loaded chunks and world metadata when the game closes.
- [x] Player spawn is restored from the saved world spawn coordinates.
- [x] Player collision-based movement, gravity, jump, sprint, and camera follow.
- [x] Hotbar selection is synchronized with the inventory's selected stack; mouse-wheel scrolling cycles through nine slots.
- [x] Left-click block mining and right-click block placement.
- [x] Number keys 1–9 select a temporary development block palette.
- [x] 5×5 nearby chunk mesh streaming as the player crosses chunk boundaries.

## Status

Phase 9 remains **in progress**, not complete. The game now has a first playable interaction loop, but it is not yet a complete Minecraft-style single-player Survival experience. The current inventory and item registry cover only a small block-item subset, not the complete 1.12.2 catalogue. HUD/inventory are basic geometry without actual item textures or count text. Crafting UI, mobs, audio, texture atlas, settings menu, and full save-selection menu remain absent. Windows workflow success does not prove a real GPU launch; desktop smoke testing remains outstanding.


## Java Edition 1.12.2 parity review — 2026-11-22

Verified against MCP 1.12.2 source:
- Survival block reach is 4.5 blocks (creative is 5.0). Desktop single-player currently runs normal survival, so both block break and place ray traces now use 4.5.
- Vanilla block damage uses digSpeed / hardness / 30 when the player can harvest, otherwise digSpeed / hardness / 100; unbreakable blocks return zero. Existing BlockBreaking.relative_hardness implements these divisors.
- The client previously forced can_harvest=True and never passed the held ItemStack to BlockBreaking. This was not Java-compatible: bare hands could receive drops from blocks requiring a specific tool.
- Client now creates a source-backed vanilla harvest-rule registry even while the starter inventory has no tools, passes the held stack into BlockBreaking, and lets the registry decide harvest eligibility. Stone/ores therefore do not drop as if mined with a suitable tool; ordinary dirt/sand remain hand-harvestable.
- Added regression coverage for empty-hand harvest requirements.

Known parity gaps (not marked complete):
- Current terrain generator is explicitly simplified; its caves, ores, terrain noise, biome blending, structures, and feature population are not byte-for-byte Java 1.12.2.
- Desktop movement still uses a simplified direct horizontal velocity model rather than the full vanilla movement-input/attribute/friction pipeline.
- Block placement is still limited to the small starter block catalogue and does not yet implement all ItemBlock callbacks, metadata/orientation, replaceability, tile entities, and all collision shapes.
- Drop resolver only maps a small starter set; block-specific loot tables and correct item IDs/drops need broader catalogue coverage.
- Current client has no full vanilla creative/survival mode selector, recipe-book equivalent, full crafting/furnace screen flow, mob spawn loop, or full world tick integration.
