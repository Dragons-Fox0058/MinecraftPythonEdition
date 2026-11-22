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
- [x] Basic block item drops, pickup into a 36-slot inventory, selected-stack placement, player health/hunger ticking, and player inventory NBT save/load for the supported block-item subset. Stone/grass/glass/gravel drop behavior has dedicated vanilla 1.12.2 rules; full loot tables remain incomplete.\n- [ ] Full vanilla item/block catalogue, crafting UI, item icons/count text, complete food/combat/damage systems, audio, video/audio settings, and full in-game server/join UI.
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
- Drop resolver now handles the registered survival subset: ores, logs/saplings/leaves, flowers/mushrooms, tall grass, dead bushes, clay, snow, glowstone, and Silk Touch variants. It is not a complete 1.12.2 loot-table catalogue; block-state metadata and mob loot still need broader coverage. Fortune/Silk Touch are read from held ItemStack NBT for supported drops.
- Desktop survival now has a 2x2 player crafting screen and a 3x3 crafting-table screen, with wood-to-planks, sticks, crafting-table, and all 15 pickaxe/axe/shovel recipes. It is not yet a full recipe-book/furnace interface.


## Java 1.12.2 block-drop correction — 2026-11-22

- Added `engine/gameplay/vanilla_drops.py` for the supported desktop subset.
- Stone now drops cobblestone (item 4), grass drops dirt (item 3), and glass drops nothing without Silk Touch.
- Gravel uses the 1.12.2 flint probability bound `10 - 3 * fortune`; flint is registered as item 318. The desktop resolver seeds its random generator from world seed and block position.
- Added grass block item ID 2 to the temporary placement palette.
- Added regression tests for stone, grass, glass/Silk Touch, and gravel/Fortune.
- This is not a complete loot-table implementation: ores, plants, metadata variants, Silk Touch/enchanted tool integration, and many other block drops still need full coverage.


## Java 1.12.2 ore drops and tool inventory — 2026-11-22

- [x] Added supported ore drops: coal, diamond, emerald, lapis lazuli (dye metadata 4), redstone, and nether quartz.
- [x] Iron and gold ore drop their own block items; Fortune does not multiply these drops.
- [x] Silk Touch resolver path returns supported ore blocks instead of their normal ore drops.
- [x] Fortune quantity multiplier uses the 1.12.2 random multiplier rule; lapis/redstone base quantities and random-call order are covered by deterministic tests.
- [x] Registered the 15 legacy 1.12.2 pickaxe, axe, and shovel items with source-era numeric IDs and material durability.
- [x] Desktop survival now uses the actual tool definitions for mining speed, harvest tier, and durability damage.
- [x] New local player files start empty-handed; the generated oak trees and player crafting grid provide the survival progression.
- [x] Fortune (ID 35) and Silk Touch (ID 33) are extracted from vanilla ItemStack ench/StoredEnchantments NBT and passed into the block drop resolver.
- [x] 2x2 and 3x3 crafting screens are connected to the desktop client; log species metadata is preserved when crafting planks, and grid contents return to inventory (or drop into the world if inventory is full) when the UI closes.
- [x] Added a first playable tree feature so survival worlds generate logs and leaves. Plant/leaf/utility drops have deterministic regression tests. Full block-state metadata and mob loot catalogues are still broader work.


CI verification — 2026-11-22:
- Python tests on the final implementation + handoff commit 37f2c6e: SUCCESS, 443 tests passed (run 45025822598).
- Windows launcher build for desktop integration commit 593e533: SUCCESS; EXE build and artifact upload steps both passed (run 45025750661).
- An intermediate run on commit 6b00163 failed because the test's scripted RNG values still reflected the old Fortune call order. The test fixture was corrected in commit be631c4; the subsequent complete suite passed.
- These checks establish automated tests and packaging only; they do not establish an interactive Windows GPU playtest or complete Java 1.12.2 parity.


## Survival crafting, enchantment NBT, trees and expanded drops — 2026-11-22

- [x] Parse legacy enchantment IDs from ItemStack NBT, including normal ench and StoredEnchantments lists.
- [x] Read Fortune III and Silk Touch from the selected held stack and apply them to supported block drops.
- [x] Register the 2x2 player crafting grid and 3x3 crafting-table grid in the desktop UI.
- [x] Add log-to-planks (preserving wood metadata), planks-to-sticks, crafting-table, and all 15 pickaxe/axe/shovel recipes.
- [x] Add crafting output collection, input consumption, and return of remaining grid ingredients on UI close/save; overflow is dropped as a world item.
- [x] Remove the temporary wooden tool starter kit. New players begin empty-handed.
- [x] Add deterministic oak tree population to generated chunks so logs are available for the crafting progression.
- [x] Expand supported drops to logs, saplings, leaves, tall grass, dead bushes, flowers/mushrooms, clay, snow, glowstone, and Silk Touch block returns.
- [x] Preserve the current supported drop set through dedicated regression tests.
- [ ] A full Java 1.12.2 block-state/metadata and mob loot catalogue is not claimed; current supported block and worldgen subsets are explicit.


## Survival equipment expansion — 2026-11-22

- [x] Added all five 1.12.2 sword tiers and all five hoe tiers with legacy item IDs and material durability.
- [x] Added sword attack-damage/material stats and hoe combat stats as explicit data.
- [x] Added the ten shaped crafting recipes, including mirrored hoe pattern matching and wood-plank metadata support.
- [x] Composed recipe managers and registered sword/hoe items in the desktop client inventory registry.
- [x] Connected sword and hoe recipes to the same 2x2/3x3 crafting interface as existing tool recipes.
- [x] Added regression tests for IDs, durability, stats, recipe counts, crafting consumption, and mirrored patterns.
- CI verification is tracked in GitHub Actions for the integration commit; no manual Windows GPU playtest is claimed.
