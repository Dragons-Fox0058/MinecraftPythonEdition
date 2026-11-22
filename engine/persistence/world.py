"""World metadata and loaded-chunk save/load for 1.12.2 Anvil worlds."""
from __future__ import annotations

import os
import uuid
import shutil
from pathlib import Path

from engine.core import BlockPos, ChunkPos, NBTTag, NBTDocument, read_nbt, write_nbt, TAG_BYTE, TAG_INT, TAG_LONG
from engine.gameplay.time import GameRules, WorldTime
from engine.gameplay.game_mode import GameMode
from engine.persistence.chunk import chunk_from_nbt, chunk_to_nbt
from engine.persistence.region import RegionFile, region_coordinates
from engine.persistence.player import save_player_data, load_player_data
from engine.gameplay.items import ItemRegistry
from engine.gameplay.player import PlayerController
from engine.world.world import World
from engine.worldgen.provider import ChunkProviderOverworld

DATA_VERSION_1_12_2 = 1343


class WorldSaveError(ValueError):
    """Invalid or incomplete world save."""


def _game_rules_to_nbt(rules: GameRules) -> dict[str, str]:
    return {name: str(value).lower() if isinstance(value, bool) else str(value)
            for name in rules.names() for value in (rules.get(name),)}


def _metadata_document(world: World) -> NBTDocument:
    data = {
        "DataVersion": NBTTag(TAG_INT, DATA_VERSION_1_12_2),
        "LevelName": world.name,
        "RandomSeed": NBTTag(TAG_LONG, int(world.seed)),
        "Time": NBTTag(TAG_LONG, world.world_time.total_time),
        "DayTime": NBTTag(TAG_LONG, world.world_time.day_time),
        "SpawnX": NBTTag(TAG_INT, int(world.spawn_point.x)),
        "SpawnY": NBTTag(TAG_INT, int(world.spawn_point.y)),
        "SpawnZ": NBTTag(TAG_INT, int(world.spawn_point.z)),
        "version": {
            "Id": NBTTag(TAG_INT, DATA_VERSION_1_12_2),
            "Name": "1.12.2",
            "Snapshot": NBTTag(TAG_BYTE, 0),
        },
        "GameRules": _game_rules_to_nbt(world.game_rules),
        "GameType": NBTTag(TAG_INT, int(world.default_game_mode)),
        "defaultGameType": NBTTag(TAG_INT, int(world.default_game_mode)),
        "initialized": NBTTag(TAG_BYTE, 1),
        "allowCommands": NBTTag(TAG_BYTE, 0),
        "hardcore": NBTTag(TAG_BYTE, 0),
        "raining": NBTTag(TAG_BYTE, 0),
        "rainTime": NBTTag(TAG_INT, 0),
        "thundering": NBTTag(TAG_BYTE, 0),
        "thunderTime": NBTTag(TAG_INT, 0),
        "clearWeatherTime": NBTTag(TAG_INT, 0),
        "generatorName": "default",
        "generatorVersion": NBTTag(TAG_INT, 1),
        "generatorOptions": "",
        "MapFeatures": NBTTag(TAG_BYTE, 1),
        "Difficulty": NBTTag(TAG_BYTE, 2),
        "DifficultyLocked": NBTTag(TAG_BYTE, 0),
    }
    return NBTDocument("", {"Data": data})


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        with open(temp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def save_world(world: World, directory: str | os.PathLike) -> None:
    if not isinstance(world, World):
        raise TypeError("world must be World")
    root = Path(directory)
    (root / "region").mkdir(parents=True, exist_ok=True)
    grouped = {}
    for chunk in world.chunk_provider.all_chunks():
        rx, rz, slot = region_coordinates(chunk.pos.x, chunk.pos.z)
        grouped.setdefault((rx, rz), []).append((slot, chunk))
    chunks_to_mark_clean = []
    for (rx, rz), chunks in grouped.items():
        region = RegionFile(root / "region" / f"r.{rx}.{rz}.mca")
        for slot, chunk in chunks:
            region.write_chunk(
                slot & 31, slot >> 5,
                chunk_to_nbt(chunk, last_update=world.world_time.total_time),
            )
            chunks_to_mark_clean.append(chunk)

    level_path = root / "level.dat"
    if level_path.is_file():
        backup = root / "level.dat_old"
        temporary_backup = root / "level.dat_old.tmp"
        try:
            shutil.copy2(level_path, temporary_backup)
            os.replace(temporary_backup, backup)
        finally:
            try:
                temporary_backup.unlink()
            except FileNotFoundError:
                pass
    _atomic_write(level_path, write_nbt(_metadata_document(world), compression="gzip"))
    # A chunk is clean only after every region and the world metadata were saved.
    for chunk in chunks_to_mark_clean:
        chunk.clear_dirty()


def load_world(directory: str | os.PathLike) -> World:
    root = Path(directory)
    level_path = root / "level.dat"
    if not level_path.is_file():
        raise WorldSaveError("level.dat is missing")
    try:
        document = read_nbt(level_path.read_bytes(), compression="gzip")
        data = document.value["Data"]
        name = str(data["LevelName"])
        world = World(name)
        world.seed = int(data["RandomSeed"])
        world.default_game_mode = GameMode.parse(int(data.get("GameType", data.get("defaultGameType", 0))))
        # Continue generating missing chunks with the saved world's seed.
        world._provider = ChunkProviderOverworld(world.seed)
        world.spawn_point = BlockPos(
            int(data.get("SpawnX", 0)),
            int(data.get("SpawnY", 64)),
            int(data.get("SpawnZ", 0)),
        )
        world.world_time = WorldTime(int(data["Time"]), int(data["DayTime"]))
        for rule, value in data.get("GameRules", {}).items():
            if rule in world.game_rules.names():
                world.game_rules.set(rule, value)
            else:
                world.game_rules.add_rule(rule, value)
        region_dir = root / "region"
        if region_dir.exists():
            for region_path in sorted(region_dir.glob("r.*.*.mca")):
                parts = region_path.stem.split(".")
                if len(parts) != 3:
                    continue
                rx, rz = int(parts[1]), int(parts[2])
                region = RegionFile(region_path)
                for local_z in range(32):
                    for local_x in range(32):
                        nbt = region.read_chunk(local_x, local_z)
                        if nbt is None:
                            continue
                        expected = ChunkPos(rx * 32 + local_x, rz * 32 + local_z)
                        chunk = chunk_from_nbt(nbt, expected_pos=expected)
                        world.chunk_provider._chunks[expected] = chunk
        return world
    except (KeyError, TypeError, ValueError, OSError) as exc:
        if isinstance(exc, WorldSaveError):
            raise
        raise WorldSaveError("malformed or unreadable 1.12.2 world save") from exc


__all__ = ["DATA_VERSION_1_12_2", "WorldSaveError", "save_world", "load_world", "save_world_player", "load_world_player"]


def save_world_player(directory: str | os.PathLike, entity, controller: PlayerController,
                      items: ItemRegistry, *, player_uuid: uuid.UUID | None = None) -> uuid.UUID:
    """Save one player's vanilla-style playerdata/<uuid>.dat file."""
    if player_uuid is None:
        player_uuid = getattr(entity, "uuid", None) or uuid.uuid4()
    elif not isinstance(player_uuid, uuid.UUID):
        player_uuid = uuid.UUID(str(player_uuid))
    path = Path(directory) / "playerdata" / f"{player_uuid}.dat"
    return save_player_data(path, entity, controller, items, player_uuid=player_uuid)


def load_world_player(directory: str | os.PathLike, player_uuid: uuid.UUID,
                      entity, controller: PlayerController, items: ItemRegistry) -> uuid.UUID:
    """Restore one player's vanilla-style playerdata/<uuid>.dat file."""
    if not isinstance(player_uuid, uuid.UUID):
        player_uuid = uuid.UUID(str(player_uuid))
    path = Path(directory) / "playerdata" / f"{player_uuid}.dat"
    return load_player_data(path, entity, controller, items)
