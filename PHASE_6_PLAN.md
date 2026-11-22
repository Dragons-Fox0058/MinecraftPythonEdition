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
- [ ] Expand block definitions to the complete 1.12.2 catalogue and verify all axe/pickaxe/shovel effective-block and harvest-level mappings against the complete source data.
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
- [x] keepInventory, doEntityDrops, and doTileDrops handling in the implemented paths.
- [x] GitHub Actions unittest workflow.

## Current automated verification

Latest successful GitHub Actions run observed during this update:
- Commit: abb4b66e50c6e6f918659c39ca881af79c121c80
- Result: 298 tests passed
- Runtime: approximately 0.60 s

This is repository CI evidence, not a claim that the game has been tested against a running Java server.

## Remaining work before Phase 6 can be called complete

- [ ] Build and verify the complete 1.12.2 item/block-item catalogue and properties; the global item registry is intentionally not auto-populated.
- [ ] Add vanilla block loot tables and correct tool/harvest-level rules.
- [ ] Populate the complete vanilla tool classes/materials and block effectiveness/harvest-level mappings; enchantment modifiers are still pending.
- [ ] Complete vanilla invulnerability-frame rules, status effects, potion effects, and source-specific damage behavior.
- [ ] Complete item entity motion, pickup events/sounds, and vanilla collision/merge behavior.
- [ ] Complete block placement state orientation, entity collision, and tile-entity placement.
- [ ] Complete crafting/furnace recipe coverage beyond the explicitly registered safe subset.
- [ ] Integrate scheduled block ticks, random ticks, weather, and tile-entity ticking with gameplay rules.
- [ ] Add integration coverage for the completed catalogue and gameplay interactions.

## Compatibility boundary

The current code is a tested gameplay foundation with selected source-backed 1.12.2 catalogues. It is not yet full vanilla gameplay compatibility. Do not mark Phase 6 complete until every remaining-work item is either implemented and tested or explicitly scoped out with a documented reason.

## Required next phases and final verification

- Finish Phase 6 before moving on.
- Phase 7 is persistence (level.dat, NBT, Anvil region/chunk save-load).
- Phase 8 is networking/protocol support.
- After Phase 8, perform the comprehensive Phase 1–8 audit, then test against a real Minecraft Java 1.12.2 server/client. Record exact versions, commands, logs, passed cases, and known incompatibilities.
- Produce a detailed handoff report at the end of each phase.