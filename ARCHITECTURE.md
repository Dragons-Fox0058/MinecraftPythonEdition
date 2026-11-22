# Minecraft Python Edition — Architecture Plan

## 1. Scope

Target: Minecraft Java Edition 1.12.2 behavior and data formats.
Not a toy voxel game. Every system listed below must eventually match 1.12.2
observable behavior, and must interoperate with real 1.12.2 worlds.

## 2. Non-goals (for now)

- Multiplayer / network protocol (deferred to a later phase)
- Resource pack loading (deferred; we ship placeholder textures first)
- Sound engine (deferred)
- Shaders / advanced rendering (deferred)

## 3. Layering

Lower layers never import from higher layers. Each arrow means depends on.

## 4. Module inventory

| Module                  | Responsibility                                            | Phase |
|-------------------------|-----------------------------------------------------------|-------|
| engine.core             | Vec3d, BlockPos, AABB, EnumFacing, math, NBT base, errors | 1     |
| engine.blocks           | Block registry, BlockState, block behaviors               | 2     |
| engine.world            | World, Chunk, ChunkProvider, lighting, tick scheduling    | 3     |
| engine.worldgen         | Noise generators, biome provider, terrain, caves, ores    | 4     |
| engine.entities         | Entity base, physics, collision, mob AI (pathfinding)     | 5     |
| engine.gameplay         | Inventory, crafting, furnace, redstone, fluids, day cycle | 6     |
| engine.persistence      | Region file (.mca) read/write, level.dat, chunk NBT       | 7     |
| engine.network          | Protocol 340 (1.12.2), packets (later)                    | 8     |
| engine.render           | Chunk mesh extraction and OpenGL renderer                 | 9     |
| engine.input            | Keyboard/mouse state and input adapters                   | 9     |
| engine.app              | Launcher, main loop, config                               | 1     |

Phases are developed in order. Later phases do not start until earlier
phases have passing tests.

## 5. Critical invariants

1. Coordinate system matches 1.12.2 exactly:
   - World coordinates: int for block positions, double for entity positions.
   - Chunk (cx, cz) covers blocks [cx*16, cx*16+15] x [cz*16, cz*16+15].
   - Y range: 0..255 inclusive. Chunk height = 256.
2. Seed handling: 1.12.2 uses Java Random (LCG) seeded from the world seed
   via JavaRandom. Exact LCG constants: 0x5DEECE66D, 0xB, 1<<48.
   Every random decision in worldgen must call the SAME JavaRandom sequence
   as vanilla does, or terrain will diverge.
3. BlockState is immutable and interned. It carries (Block, properties dict).
   BlockPos -> IBlockState lookup is the hot path. Must be O(1).
4. Chunk storage: 16x16x256 blocks = 65,536 entries. Internally store as
   numpy.uint16 block state IDs (index into a global palette) plus a
   numpy.uint8 light array (4 bits sky + 4 bits block) packed per block.
5. Persistence: 1.12.2 uses Anvil (.mca region files). Region files hold
   chunks in NBT, zlib-compressed. We must read and write the EXACT SAME
   format so worlds are interchangeable.
6. No silent failures: every parser (NBT, region, level.dat) raises a typed
   exception on malformed input. Tests cover round-trips.

## 6. Development order and rationale

| Phase | Deliverable                                  | Why first                                    |
|-------|----------------------------------------------|----------------------------------------------|
| 1     | core (math, NBT, errors) + app skeleton      | Everything else depends on these primitives  |
| 2     | blocks (registry, BlockState, behaviors)     | World needs block types before it can tick   |
| 3     | world (chunk, storage, lighting, ticks)      | Foundation for gameplay and entities         |
| 4     | worldgen (biomes, terrain, caves, ores)      | Produces the world that phase 5+ consumes    |
| 5     | entities (base, physics, collision, AI)      | Requires a populated world                   |
| 6     | gameplay (inventory, crafting, redstone)     | Requires blocks + entities                   |
| 7     | persistence (.mca, level.dat)                | Requires stable chunk format                 |
| 8     | network                                      | Requires full game state                     |
| 9     | render, input                                | Requires full game state                     |

## 7. Testing strategy

- Every module ships with tests/test_<module>.py.
- Golden values: where 1.12.2 has deterministic output (NBT binary layout,
  JavaRandom sequence, block hardness table), tests check against hand-verified
  constants extracted from the JAR inventory.
- Integration tests at phase boundaries: e.g. test_worldgen_matches_chunk_nbt
  loads a real .mca region from private-input/ (not committed) and compares
  the decoded chunk to our in-memory chunk.

## 8. Performance notes

- Python is ~50x slower than Java. Accept it for logic, not for hot loops.
- Hot loops: chunk mesh generation, light propagation, entity ticking.
  These will be rewritten in NumPy (or Cython if NumPy is not enough).
- Everything else stays pure Python for readability.
- Target: 60 FPS at render distance 8 chunks on a mid-range machine.
  If unreachable, profile and rewrite the bottleneck, do not guess.
