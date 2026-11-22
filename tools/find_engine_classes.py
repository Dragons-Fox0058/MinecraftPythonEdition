#!/usr/bin/env python3.12
"""
Minecraft 1.12.2 engine class inventory — v2 classifier.

Fixes:
- Rule order: specific sub-packages and specific class names BEFORE their
  parent package. E.g. BlockRedstone* -> REDSTONE before BLOCK catches it.
- Adds FLUID, LIGHTING, PHYSICS detection via specific class-name rules that
  fire before the generic BLOCK / WORLD rules.
- Adds a "runtime priority" tier to each class:
    CORE    = engine must implement this
    SUPPORT = helpful but not first-pass
    CLIENT  = rendering / GUI / audio (later phase)
    SKIP    = pure vanilla Java plumbing (e.g. CrashReport, Log4j wrappers)
- Emits per-category and per-tier summaries so we can plan phases.
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING_INDEX = ROOT / "research" / "mapping_index.json"
OUTPUT = ROOT / "research" / "engine_class_inventory.txt"
SUMMARY = ROOT / "research" / "engine_class_summary.txt"

# (category, tier, prefixes, exact_simple_names, keyword_fallback)
# First matching rule wins. Order matters — most specific first.
RULES = [
    # --- Phase 0: trivial / non-game systems that we can skip ---
    ("SKIP_PLUMBING", "SKIP",
     ("net/minecraft/crash", "net/minecraft/util/text/",
      "net/minecraft/advancements", "net/minecraft/scoreboard",
      "net/minecraft/stats", "net/minecraft/client/gui/",
      "net/minecraft/client/renderer/", "net/minecraft/client/resources/",
      "net/minecraft/client/audio/", "net/minecraft/client/main/",
      "net/minecraft/client/multiplayer/"),
     (), ()),

    # --- Phase 0b: server networking (multiplayer later) ---
    ("NETWORK", "SUPPORT",
     ("net/minecraft/network", "net/minecraft/server/management",
      "net/minecraft/server/"), (), ()),

    # --- Specific gameplay overrides (must come BEFORE parent block/world) ---
    ("REDSTONE", "CORE",
     (), (),
     (r"^BlockRedstone", r"^BlockPiston", r"^TileEntityPiston",
      r"^BlockDispenser", r"^BlockDropper", r"^BlockObserver",
      r"^BlockHopper", r"^BlockRepeater", r"^BlockComparator")),
    ("FLUID", "CORE",
     ("net/minecraft/block/material",),
     (),
     (r"^BlockLiquid", r"^BlockStaticLiquid", r"^BlockDynamicLiquid",
      r"^BlockFluid", r"^BlockWater", r"^BlockLava")),
    ("LIGHTING", "CORE",
     (), (),
     (r"^EnumSkyBlock", r"^World\$", r"^BlockGlass", r"^BlockStainedGlass",
      r"^BlockTorch", r"^BlockGlowstone", r"^BlockLight")),
    ("PHYSICS", "CORE",
     (), ("MoverType",),
     (r"^AxisAlignedBB", r"^RayTraceResult", r"^MovingObjectPosition",
      r"^BlockPos$", r"^Vec3d$", r"^EnumFacing$")),
    ("INVENTORY", "CORE",
     ("net/minecraft/inventory", "net/minecraft/crafting", "net/minecraft/tileentity/TileEntityFurnace",
      "net/minecraft/tileentity/TileEntityChest", "net/minecraft/tileentity/TileEntityHopper"),
     (), ()),
    ("NBT", "CORE", ("net/minecraft/nbt",), (), ()),
    ("BIOME", "CORE", ("net/minecraft/world/biome",), (), ()),
    ("WORLDGEN", "CORE", ("net/minecraft/world/gen",), (), ()),
    ("MOB_AI", "CORE", ("net/minecraft/entity/ai", "net/minecraft/pathfinding"), (), ()),
    ("ENCHANT", "SUPPORT", ("net/minecraft/enchantment",), (), ()),
    ("POTION", "SUPPORT", ("net/minecraft/potion",), (), ()),

    # --- Core entities ---
    ("ENTITY", "CORE", ("net/minecraft/entity",), (), ()),

    # --- Blocks and items ---
    ("BLOCK_STATE", "CORE", ("net/minecraft/block/state",), (), ()),
    ("BLOCK", "CORE", ("net/minecraft/block",), (), ()),
    ("ITEM", "CORE", ("net/minecraft/item",), (), ()),

    # --- World / chunk (after gen/biome) ---
    ("WORLD_CHUNK", "CORE",
     ("net/minecraft/world/chunk", "net/minecraft/world/storage",
      "net/minecraft/world/World", "net/minecraft/util/math/ChunkPos"), (), ()),

    # --- Text / util / command ---
    ("TEXT", "SUPPORT", ("net/minecraft/util/text",), (), ()),
    ("COMMAND", "SUPPORT", ("net/minecraft/command",), (), ()),
    ("UTIL", "SUPPORT", ("net/minecraft/util",), (), ()),
    ("CORE_MISC", "SUPPORT",
     ("net/minecraft/",), (), ()),  # catch-all: anything net/minecraft left
]


def classify(name: str):
    simple = name.rsplit("/", 1)[-1]
    for cat, tier, prefixes, exact, patterns in RULES:
        for p in prefixes:
            if name.startswith(p):
                return cat, tier, f"pkg:{p}"
        if simple in exact:
            return cat, tier, f"exact:{simple}"
        for pat in patterns:
            if re.search(pat, simple):
                return cat, tier, f"rx:{pat}"
    return "UNCLASSIFIED", "UNKNOWN", "none"


def main():
    data = json.loads(MAPPING_INDEX.read_text())
    deobf_names = sorted(set(data["classes"].values()))

    buckets = defaultdict(list)
    tier_of = {}
    reasons = Counter()
    for name in deobf_names:
        cat, tier, rule = classify(name)
        buckets[cat].append(name)
        tier_of[name] = tier
        reasons[(cat, tier, rule)] += 1

    with OUTPUT.open("w") as f:
        f.write("# Minecraft 1.12.2 — Refined Engine Class Inventory v2\n")
        f.write("# Source: research/mapping_index.json (MCP Stable 39)\n")
        f.write("# Tier: CORE / SUPPORT / CLIENT / SKIP\n\n")
        for cat in sorted(buckets):
            f.write(f"\n===== {cat} =====\n")
            for name in sorted(buckets[cat]):
                f.write(f"[{tier_of[name]:<7}] {name}\n")

    # Summary by category and by tier.
    tier_counts = Counter(tier_of.values())
    with SUMMARY.open("w") as f:
        f.write("# Category counts\n\n")
        f.write(f"{'CATEGORY':<16} {'CORE':>5} {'SUPPORT':>8} {'CLIENT':>7} {'SKIP':>5} {'TOTAL':>6}\n")
        f.write("-" * 52 + "\n")
        cat_tier = defaultdict(Counter)
        for name, tier in tier_of.items():
            cat = next(c for c in buckets if name in buckets[c])
            cat_tier[cat][tier] += 1
        for cat in sorted(buckets):
            c = cat_tier[cat]
            f.write(f"{cat:<16} {c['CORE']:>5} {c['SUPPORT']:>8} {c['CLIENT']:>7} {c['SKIP']:>5} {sum(c.values()):>6}\n")
        f.write("\n# Tier totals\n\n")
        for t in ("CORE", "SUPPORT", "CLIENT", "SKIP", "UNKNOWN"):
            f.write(f"{t:<10} {tier_counts[t]:>5}\n")

    print(f"Total classes: {len(deobf_names)}\n")
    print(f"{'CATEGORY':<16} {'CORE':>5} {'SUPPORT':>8} {'CLIENT':>7} {'SKIP':>5} {'TOTAL':>6}")
    print("-" * 52)
    for cat in sorted(buckets):
        c = cat_tier[cat]
        print(f"{cat:<16} {c['CORE']:>5} {c['SUPPORT']:>8} {c['CLIENT']:>7} {c['SKIP']:>5} {sum(c.values()):>6}")
    print()
    for t in ("CORE", "SUPPORT", "CLIENT", "SKIP", "UNKNOWN"):
        print(f"{t:<10} {tier_counts[t]:>5}")
    print(f"\nWrote {OUTPUT}")
    print(f"Wrote {SUMMARY}")


if __name__ == "__main__":
    main()
