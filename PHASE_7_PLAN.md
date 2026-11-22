# Phase 7 — Persistence (Java Edition 1.12.2)

## Implemented

- [x] NBT reader/writer for all standard tag IDs 0–12.
- [x] Named root compounds, typed scalar wrappers, lists, compounds, byte/int/long arrays.
- [x] Uncompressed, gzip, and zlib NBT input/output.
- [x] Input, nesting, and decompressed-size bounds; malformed/truncated/trailing input raises typed errors.
- [x] Anvil region (.mca) location table reader and chunk payload reader.
- [x] Anvil region writer with sector allocation, compaction, timestamps, and atomic replacement.
- [x] Chunk section conversion for 1.12.2 Blocks/Data/Add/BlockLight/SkyLight arrays, including 12-bit block IDs and metadata.
- [x] Chunk coordinate validation, biome byte array, calculated heightmap, and standard empty entity/tile-entity/tick lists.
- [x] Gzip level.dat with 1.12.2 DataVersion 1343, seed, world clock, and game rules.
- [x] World save/load for loaded chunks across positive and negative region coordinates.
- [x] Player .dat save/load for transform, health, inventory, armor, offhand, hunger, selected slot, UUID, and active effects.
- [x] Atomic writes for level.dat and player data.
- [x] Unit tests for malformed NBT, compression bounds, chunk round-trips, region sector compaction, world metadata, and player data.

## Verification

The Python unit-test workflow is the automated evidence. It does not by itself prove that a generated world can be opened by the official 1.12.2 client/server. That compatibility test remains required.

## Remaining compatibility work

- [ ] Add fixtures from genuine 1.12.2 worlds and verify byte-level NBT/region compatibility.
- [ ] Verify the complete 1.12.2 chunk schema, including real biome arrays, heightmap semantics, lighting, populated flags, and tile entities.
- [ ] Persist and restore all supported entities, dropped items, tile entities, scheduled block ticks, and world-specific metadata.
- [ ] Verify crash recovery and backup/old-level.dat behavior against vanilla save semantics.
- [ ] Verify opening, modifying, and reopening a real world with the official 1.12.2 server/client.

## Status

Persistence foundations are implemented. Phase 7 is **not certified complete** until the remaining compatibility fixtures and real-world round-trip tests pass.
