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

## Requirements
- Preserve existing Phase 1–5 code unless an integration fix is necessary.
- Compare behavior against Java 1.12.2 references.
- Add tests for every implemented feature.
- Do not claim compatibility without verification.
- Produce a detailed handoff report at the end of Phase 6.
- Perform the comprehensive Phase 1–6 audit afterward.


## Implementation status — 2026-11-22

The following code foundations have been added to the repository:

- [x] Item, ItemRegistry, ItemStack (verified vanilla item catalogue still pending)
- [x] Inventory, hotbar, armor slots, and offhand
- [x] Block breaking progress and optional injected loot resolver
- [x] Block placement with an explicit Item-to-Block resolver
- [x] Shaped and shapeless crafting recipe engine with alternative ingredients and output stack validation
- [x] Furnace fuel and smelting recipe engine with slot insertion/extraction and progress state
- [x] Metadata-aware food properties and food registry; hunger, exhaustion, regeneration, and starvation manager
- [x] Dropped item entities and inventory pickup
- [x] World clock and typed game rules, integrated into World.tick
- [x] Player gameplay controller, block ray tracing, food use, and death drops honoring keepInventory
- [x] Cross-system break → drop → pickup → place regression test
- [x] GitHub Actions unittest workflow

### Not yet complete / not to be claimed as vanilla-compatible

- The global item registry is intentionally empty until item IDs and item properties are verified against the 1.12.2 data.
- Vanilla recipe, fuel, food, and block-loot catalogues have not been populated.
- Tool speed, harvest-level requirements, enchantments, potion effects, armor reduction, and damage-source rules are not yet fully implemented.
- Furnace container-item returns and smelting experience collection are not yet implemented.
- Item entity merging, randomized toss motion, pickup sound/events, and complete collision behavior are not yet implemented.
- Placement does not yet include all vanilla block-state orientation, player collision, or tile-entity rules.
- Ray tracing currently uses the engine's available block collision boxes; complex partial block shapes and entity ray tracing remain future work.
- World ticking does not yet implement scheduled block ticks, random ticks, weather simulation, or full vanilla tile-entity ticking.
- Persistence integration and the full Phase 1–6 audit remain deferred until Phase 6 is finished.

The checklist records implementation progress only. Compatibility claims require reference-based verification and passing regression tests.
