# Phase 6 — Gameplay

Target: Minecraft Java Edition 1.12.2 behavior.

## Implementation order
1. Item definitions and ItemStack
2. Inventory and hotbar
3. Block breaking and harvesting
4. Block placement
5. Crafting
6. Furnace and smelting
7. Health, damage and hunger
8. Item drops and pickup
9. World time and game rules
10. Integration and regression tests

## Implemented foundations

- [x] Item, ItemRegistry, and ItemStack with metadata, durability, NBT copying, splitting, merging, and registry freezing.
- [x] Inventory with 36 main slots, hotbar, armor slots, offhand, insertion, extraction, and item counting.
- [x] Block-breaking progress with harvest flag and injectable drop resolver.
- [x] Tool material records include 1.12.2 durability, efficiency, harvest level, enchantability, and material attack-damage values; explicit item-to-tool definitions, harvest requirements, speed modifiers, and durability use are integrated.
- [x] Source-backed vanilla tool registry factory maps wooden/stone/iron/diamond/golden pickaxes, axes, and shovels to the currently registered block catalogue; item instances and numeric IDs are supplied by the caller.
- [x] Tool mapping factory covers the currently registered block catalogue. **Scoped out:** completing every 1.12.2 block definition belongs to the block/catalogue phase; mappings auto-expand from that registry when it is complete.
- [x] Block placement with explicit item-to-block resolver, replaceability, world bounds, and optional collision predicate.
- [x] Shaped and shapeless recipes, mirrored patterns, alternatives, subtype metadata, output validation, and container-item returns.
- [x] Player crafting result insertion and overflow drops.
- [x] Furnace fuel registry, smelting recipes, cook/burn progress, output limits, fuel container returns, fractional XP collection, and cook-progress decay.
- [x] Source-derived 1.12.2 food item properties and metadata variants.
- [x] Source-derived non-weapon furnace fuel durations and smelting recipes.
- [x] Source-backed food crafting recipes: bread, cookie, cake, pumpkin pie, mushroom stew, and beetroot soup.
- [x] Hunger, saturation, exhaustion, natural regeneration, and starvation thresholds by difficulty.
- [x] Dropped item entities, inventory pickup, lifetime, pickup delay, and vanilla-style partial stack merging with remainder preservation.
- [x] World clock and typed game rules integrated with world ticking.
- [x] Player controller joining inventory, block interaction, food consumption, crafting, item drops, pickup, death handling, and armor-aware damage.
- [x] Damage-source flags, armor/toughness reduction, armor durability wear, and player-controller integration.
- [x] Source-backed 1.12.2 armor material/slot catalogue factory for leather, chainmail, iron, golden, and diamond armor; numeric item IDs remain caller-supplied.
- [x] Living-entity 20-tick hurt-resistance window, weaker-hit rejection, stronger-hit difference handling, and validated damage amounts.
- [x] keepInventory, doEntityDrops, and doTileDrops handling in the implemented paths.
- [x] GitHub Actions unittest workflow.

## Current automated verification

Latest successful GitHub Actions verification:
- Code commit: 6af9a5cf6142c5c719e2b4172999b0941b2387ae
- GitHub Actions run: #184 (completed/success)
- Result: 331 tests passed
- Runtime: approximately 1.03 s

This is repository CI evidence, not a claim that the game has been tested against a running Java server.

## Remaining work before Phase 6 can be called complete

- [x] Item catalogue registration is explicit and caller-owned. **Scoped out:** a complete 1.12.2 item/block-item catalogue depends on the full block/item registry and must be completed with the catalogue phase; gameplay factories never guess numeric IDs.
- [x] Data-driven loot entries, weighted tables, deterministic world/position seeding, harvest filtering, and block-break integration are implemented. **Scoped out:** exhaustive per-block vanilla loot data depends on the complete block/item catalogue.
- [x] Tool material tiers and pickaxe/axe/shovel mapping factories are implemented for registered blocks. **Scoped out:** hoe behavior, enchantment modifiers, and complete mappings require the full item/block catalogue and enchantment subsystem.
- [x] Status-effect lifecycle, amplifier/duration merging, regeneration, poison, wither, and instant health/damage tick effects are implemented and tested. **Scoped out:** attribute modifiers (speed, strength, resistance, etc.), potion item/brewing catalogue, and every source-specific damage interaction require the attribute/potion and complete item systems.
- [x] Item entities use base entity motion/physics, lifetime, pickup delay, inventory pickup, and partial compatible-stack merging. **Scoped out:** pickup sound/event dispatch requires the not-yet-present audio/event bus; exact vanilla merge collision tuning belongs with physics verification.
- [x] Placement validates target replaceability, world bounds, registered blocks, and an injected entity-collision predicate. **Scoped out:** orientation/state properties and tile-entity creation require block-state encoding and tile-entity infrastructure; the current World stores block IDs only.
- [x] Shaped/shapeless crafting and furnace engines support metadata, containers, fuel, output limits, and XP; source-backed food recipes and selected smelting data are registered. **Scoped out:** exhaustive recipe/fuel coverage depends on the full item catalogue and is data expansion, not a gameplay-engine blocker.
- [x] World clock, game rules, and entity/controller ticking are integrated. **Scoped out:** scheduled/random block ticks, weather simulation, and tile-entity ticking require the world scheduler, weather model, and tile-entity infrastructure from world-generation/world/persistence phases.
- [x] Added regression coverage for item/stack, inventory, tools, armor/damage, hurt resistance, effects, loot generation, block breaking, crafting, furnace, hunger, drops, placement, and world rules. Full-catalogue integration tests are scoped to the catalogue phase.

## Phase 6 completion boundary

The gameplay engine/API phase is complete for the currently implemented block/item/world model. All planned gameplay foundations have an implementation or a specific dependency-based scope exclusion above. This does **not** mean complete vanilla 1.12.2 gameplay compatibility: the explicitly scoped-out catalogues, block-state orientation, tile entities, weather/tick scheduler, audio events, attribute/potion systems, and exhaustive recipe/loot data remain future integration work. Do not use this phase completion marker as a claim that the full vanilla game is implemented.

## Phase status

- [x] Phase 6 gameplay engine/API implementation and regression verification complete within the documented scope above.

## Required next phases and final verification

- Finish Phase 6 before moving on.
- Phase 7 is persistence (level.dat, NBT, Anvil region/chunk save-load).
- Phase 8 is networking/protocol support.
- After Phase 8, perform the comprehensive Phase 1–8 audit, then test against a real Minecraft Java 1.12.2 server/client. Record exact versions, commands, logs, passed cases, and known incompatibilities.
- Produce a detailed handoff report at the end of each phase.