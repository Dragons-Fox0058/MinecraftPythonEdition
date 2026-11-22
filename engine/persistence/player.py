"""Minecraft 1.12.2 player NBT persistence for entity and inventory state."""
from __future__ import annotations

import uuid
import os
from pathlib import Path

from engine.core import NBTTag, NBTDocument, NBTList, Vec3d, write_nbt, read_nbt
from engine.core.nbt import TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE, TAG_COMPOUND
from engine.gameplay.effects import EffectType, StatusEffect
from engine.gameplay.items import ItemRegistry, ItemStack
from engine.gameplay.player import PlayerController
from engine.gameplay.game_mode import GameMode


class PlayerDataError(ValueError):
    """Invalid player NBT or incompatible item registry."""


def _plain(value):
    return value.value if isinstance(value, NBTTag) else value


def _signed64(value: int) -> int:
    return value - (1 << 64) if value >= (1 << 63) else value


def player_to_nbt(entity, controller: PlayerController, items: ItemRegistry,
                  *, player_uuid: uuid.UUID | None = None) -> NBTDocument:
    if not isinstance(controller, PlayerController):
        raise TypeError("controller must be PlayerController")
    if not isinstance(items, ItemRegistry):
        raise TypeError("items must be ItemRegistry")
    player_uuid = player_uuid or getattr(entity, "uuid", None) or uuid.uuid4()
    if not isinstance(player_uuid, uuid.UUID):
        player_uuid = uuid.UUID(str(player_uuid))
    entity.uuid = player_uuid

    inventory = []
    def add_stack(slot: int, stack: ItemStack):
        if stack.is_empty:
            return
        if stack.item.item_id > 32767:
            raise PlayerDataError("1.12.2 item ID does not fit signed short")
        damage = stack.damage if stack.item.is_damageable else stack.metadata
        entry = {
            "Slot": NBTTag(TAG_BYTE, slot),
            "id": NBTTag(TAG_SHORT, stack.item.item_id),
            "Count": NBTTag(TAG_BYTE, stack.count),
            "Damage": NBTTag(TAG_SHORT, damage),
        }
        if stack.nbt:
            entry["tag"] = stack.nbt
        inventory.append(entry)

    for index, stack in enumerate(controller.inventory.slots):
        add_stack(index, stack)
    # Vanilla player inventory armor slots: boots=100 through helmet=103.
    for index, stack in enumerate(controller.inventory.armor):
        add_stack(103 - index, stack)
    add_stack(-106, controller.inventory.offhand)

    active_effects = []
    for effect in entity.status_effects.active():
        active_effects.append({
            "Id": NBTTag(TAG_BYTE, int(effect.effect)),
            "Amplifier": NBTTag(TAG_BYTE, effect.amplifier if effect.amplifier < 128 else effect.amplifier - 256),
            "Duration": NBTTag(TAG_INT, effect.duration),
            "Ambient": NBTTag(TAG_BYTE, int(effect.ambient)),
            "ShowParticles": NBTTag(TAG_BYTE, int(effect.show_particles)),
        })

    pos = NBTList(TAG_DOUBLE, (float(entity.pos.x), float(entity.pos.y), float(entity.pos.z)))
    motion = NBTList(TAG_DOUBLE, (float(entity.motion.x), float(entity.motion.y), float(entity.motion.z)))
    rotation = NBTList(TAG_FLOAT, (float(getattr(entity, "yaw", 0.0)), float(getattr(entity, "pitch", 0.0))))
    uid = player_uuid.int
    data = {
        "Pos": pos,
        "Motion": motion,
        "Rotation": rotation,
        "FallDistance": NBTTag(TAG_FLOAT, float(entity.fall_distance)),
        "Fire": NBTTag(TAG_SHORT, -1),
        "Air": NBTTag(TAG_SHORT, 300),
        "OnGround": NBTTag(TAG_BYTE, int(entity.on_ground)),
        "Dimension": NBTTag(TAG_INT, 0),
        "Invulnerable": NBTTag(TAG_BYTE, 0),
        "PortalCooldown": NBTTag(TAG_INT, 0),
        "UUIDMost": NBTTag(TAG_LONG, _signed64(uid >> 64)),
        "UUIDLeast": NBTTag(TAG_LONG, _signed64(uid & ((1 << 64) - 1))),
        "Health": NBTTag(TAG_FLOAT, float(entity.health)),
        "playerGameType": NBTTag(TAG_INT, int(controller.game_mode)),
        "foodLevel": NBTTag(TAG_INT, controller.hunger.food_level),
        "foodSaturationLevel": NBTTag(TAG_FLOAT, float(controller.hunger.saturation)),
        "foodExhaustionLevel": NBTTag(TAG_FLOAT, float(controller.hunger.exhaustion)),
        "foodTickTimer": NBTTag(TAG_INT, controller.hunger.food_timer),
        "SelectedItemSlot": NBTTag(TAG_INT, controller.inventory.selected_hotbar_slot),
        "Inventory": NBTList(TAG_COMPOUND, tuple(inventory)),
        "ActiveEffects": NBTList(TAG_COMPOUND, tuple(active_effects)),
    }
    return NBTDocument("", data)


def player_from_nbt(document: NBTDocument, entity, controller: PlayerController,
                    items: ItemRegistry) -> uuid.UUID:
    if not isinstance(document, NBTDocument):
        raise TypeError("document must be NBTDocument")
    if not isinstance(controller, PlayerController) or not isinstance(items, ItemRegistry):
        raise TypeError("controller and items must be valid registries")
    try:
        data = document.value
        pos = data["Pos"].values
        motion = data["Motion"].values
        rotation = data["Rotation"].values
        if len(pos) != 3 or len(motion) != 3 or len(rotation) != 2:
            raise PlayerDataError("invalid player vector list lengths")
        entity.set_position(*map(float, pos))
        entity.motion = Vec3d(*map(float, motion))
        if hasattr(entity, "yaw"): entity.yaw = float(rotation[0])
        if hasattr(entity, "pitch"): entity.pitch = float(rotation[1])
        entity.fall_distance = float(data.get("FallDistance", 0.0))
        entity.on_ground = bool(data.get("OnGround", 0))
        entity.health = max(0.0, min(entity.max_health, float(data.get("Health", entity.max_health))))
        entity.dead = entity.health <= 0
        controller.set_game_mode(int(data.get("playerGameType", int(getattr(controller.world, "default_game_mode", GameMode.SURVIVAL)))))

        controller.inventory.clear()
        for entry in data.get("Inventory", NBTList(TAG_COMPOUND, ())).values:
            item_id = int(_plain(entry["id"]))
            item = items.get_by_id(item_id)
            if item is None:
                continue
            count = int(_plain(entry["Count"]))
            slot = int(_plain(entry["Slot"]))
            raw_damage = int(_plain(entry.get("Damage", 0)))
            metadata = 0 if item.is_damageable else (raw_damage if item.has_subtypes else 0)
            durability = raw_damage if item.is_damageable else 0
            stack = ItemStack(item, count, metadata=metadata, damage=durability,
                              nbt=entry.get("tag"))
            if 0 <= slot < controller.inventory.main_size:
                controller.inventory.set_slot(slot, stack)
            elif 100 <= slot <= 103:
                controller.inventory.set_armor_slot(103 - slot, stack)
            elif slot == -106:
                controller.inventory.set_offhand(stack)

        selected = int(data.get("SelectedItemSlot", 0))
        if 0 <= selected < controller.inventory.hotbar_size:
            controller.inventory.select_hotbar_slot(selected)
        controller.hunger.food_level = max(0, min(20, int(data.get("foodLevel", 20))))
        controller.hunger.saturation = max(
            0.0, min(float(controller.hunger.food_level), float(data.get("foodSaturationLevel", 5.0)))
        )
        controller.hunger.exhaustion = max(0.0, min(40.0, float(data.get("foodExhaustionLevel", 0.0))))
        controller.hunger.food_timer = max(0, int(data.get("foodTickTimer", 0)))

        entity.status_effects = type(entity.status_effects)()
        for effect in data.get("ActiveEffects", NBTList(TAG_COMPOUND, ())).values:
            try:
                kind = EffectType(int(effect["Id"]))
                entity.status_effects.add(StatusEffect(
                    kind, int(effect["Duration"]), int(_plain(effect.get("Amplifier", 0))) & 0xFF,
                    bool(effect.get("Ambient", 0)), bool(effect.get("ShowParticles", 1)),
                ))
            except (ValueError, KeyError):
                continue

        most = int(_plain(data.get("UUIDMost", 0))) & ((1 << 64) - 1)
        least = int(_plain(data.get("UUIDLeast", 0))) & ((1 << 64) - 1)
        result_uuid = uuid.UUID(int=(most << 64) | least)
        entity.uuid = result_uuid
        return result_uuid
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, PlayerDataError):
            raise
        raise PlayerDataError("malformed player NBT") from exc

def save_player_data(path, entity, controller: PlayerController,
                     items: ItemRegistry, *, player_uuid: uuid.UUID | None = None) -> uuid.UUID:
    document = player_to_nbt(entity, controller, items, player_uuid=player_uuid)
    uid = entity.uuid
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        with open(temporary, "wb") as handle:
            handle.write(write_nbt(document, compression="gzip"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return uid


def load_player_data(path, entity, controller: PlayerController,
                     items: ItemRegistry) -> uuid.UUID:
    try:
        document = read_nbt(Path(path).read_bytes(), compression="gzip")
    except (OSError, ValueError) as exc:
        raise PlayerDataError("unable to read player data file") from exc
    return player_from_nbt(document, entity, controller, items)


__all__ = ["PlayerDataError", "player_to_nbt", "player_from_nbt", "save_player_data", "load_player_data"]
