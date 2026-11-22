"""Protocol-340 entity spawn and movement packet decoders."""
from __future__ import annotations

import math
import struct
import uuid
from dataclasses import dataclass

from engine.network.codec import PacketBuffer, ProtocolError


def _angle(value: int) -> float:
    return (value & 0xFF) * (360.0 / 256.0)


def _bool(value: int) -> bool:
    if value not in (0, 1):
        raise ProtocolError("invalid entity on-ground boolean")
    return bool(value)


@dataclass(frozen=True)
class SpawnObject:
    entity_id: int
    entity_uuid: uuid.UUID
    object_type: int
    x: float
    y: float
    z: float
    pitch: float
    yaw: float
    data: int
    velocity: tuple[float, float, float]


@dataclass(frozen=True)
class SpawnMob:
    entity_id: int
    entity_uuid: uuid.UUID
    mob_type: int
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    head_yaw: float
    velocity: tuple[float, float, float]
    metadata: bytes


@dataclass(frozen=True)
class SpawnPlayer:
    entity_id: int
    player_uuid: uuid.UUID
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    metadata: bytes


@dataclass(frozen=True)
class SpawnExperienceOrb:
    entity_id: int
    x: float
    y: float
    z: float
    experience: int


@dataclass(frozen=True)
class EntityRelativeMove:
    entity_id: int
    dx: float
    dy: float
    dz: float
    yaw: float | None
    pitch: float | None
    on_ground: bool


@dataclass(frozen=True)
class EntityTeleport:
    entity_id: int
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    on_ground: bool


@dataclass(frozen=True)
class EntityVelocity:
    entity_id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class DestroyEntities:
    entity_ids: tuple[int, ...]


def _read_uuid(buf: PacketBuffer) -> uuid.UUID:
    return uuid.UUID(bytes=buf.read(16))


def _read_velocity(buf: PacketBuffer) -> tuple[float, float, float]:
    x, y, z = struct.unpack(">hhh", buf.read(6))
    return x / 8000.0, y / 8000.0, z / 8000.0


def _validate_coordinates(values) -> None:
    if not all(math.isfinite(v) for v in values):
        raise ProtocolError("entity coordinates must be finite")


def decode_spawn_object(payload: bytes) -> SpawnObject:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    entity_uuid = _read_uuid(buf)
    object_type = buf.read(1)[0]
    x, y, z = struct.unpack(">ddd", buf.read(24))
    pitch, yaw = (_angle(v) for v in buf.read(2))
    data = struct.unpack(">i", buf.read(4))[0]
    velocity = _read_velocity(buf)
    if buf.remaining:
        raise ProtocolError("trailing Spawn Object payload")
    _validate_coordinates((x, y, z))
    return SpawnObject(entity_id, entity_uuid, object_type, x, y, z,
                       pitch, yaw, data, velocity)


def decode_spawn_mob(payload: bytes) -> SpawnMob:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    entity_uuid = _read_uuid(buf)
    mob_type = buf.read_varint()
    x, y, z = struct.unpack(">ddd", buf.read(24))
    yaw, pitch, head_yaw = (_angle(v) for v in buf.read(3))
    velocity = _read_velocity(buf)
    metadata = buf.read_remaining()
    _validate_coordinates((x, y, z))
    return SpawnMob(entity_id, entity_uuid, mob_type, x, y, z,
                    yaw, pitch, head_yaw, velocity, metadata)


def decode_spawn_player(payload: bytes) -> SpawnPlayer:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    player_uuid = _read_uuid(buf)
    x, y, z = struct.unpack(">ddd", buf.read(24))
    yaw, pitch = (_angle(v) for v in buf.read(2))
    metadata = buf.read_remaining()
    _validate_coordinates((x, y, z))
    return SpawnPlayer(entity_id, player_uuid, x, y, z, yaw, pitch, metadata)


def decode_spawn_experience_orb(payload: bytes) -> SpawnExperienceOrb:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    x, y, z = struct.unpack(">ddd", buf.read(24))
    experience = struct.unpack(">h", buf.read(2))[0]
    if buf.remaining:
        raise ProtocolError("trailing Spawn Experience Orb payload")
    _validate_coordinates((x, y, z))
    if experience < 0:
        raise ProtocolError("experience orb value cannot be negative")
    return SpawnExperienceOrb(entity_id, x, y, z, experience)


def decode_entity_relative_move(payload: bytes, *, with_look: bool = False,
                                look_only: bool = False) -> EntityRelativeMove:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    if look_only:
        dx = dy = dz = 0.0
    else:
        sx, sy, sz = struct.unpack(">hhh", buf.read(6))
        dx, dy, dz = sx / 4096.0, sy / 4096.0, sz / 4096.0
    yaw = pitch = None
    if with_look or look_only:
        yaw, pitch = (_angle(v) for v in buf.read(2))
    on_ground = _bool(buf.read(1)[0])
    if buf.remaining:
        raise ProtocolError("trailing entity movement payload")
    return EntityRelativeMove(entity_id, dx, dy, dz, yaw, pitch, on_ground)


def decode_entity_teleport(payload: bytes) -> EntityTeleport:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    x, y, z = struct.unpack(">ddd", buf.read(24))
    yaw, pitch = (_angle(v) for v in buf.read(2))
    on_ground = _bool(buf.read(1)[0])
    if buf.remaining:
        raise ProtocolError("trailing Entity Teleport payload")
    _validate_coordinates((x, y, z))
    return EntityTeleport(entity_id, x, y, z, yaw, pitch, on_ground)


def decode_entity_velocity(payload: bytes) -> EntityVelocity:
    buf = PacketBuffer(payload)
    entity_id = buf.read_varint()
    x, y, z = _read_velocity(buf)
    if buf.remaining:
        raise ProtocolError("trailing Entity Velocity payload")
    return EntityVelocity(entity_id, x, y, z)


def decode_destroy_entities(payload: bytes) -> DestroyEntities:
    buf = PacketBuffer(payload)
    count = buf.read_varint()
    if not 0 <= count <= 4096:
        raise ProtocolError("invalid Destroy Entities count")
    entity_ids = tuple(buf.read_varint() for _ in range(count))
    if any(entity_id < 0 for entity_id in entity_ids) or buf.remaining:
        raise ProtocolError("invalid Destroy Entities payload")
    return DestroyEntities(entity_ids)


__all__ = [
    "SpawnObject", "SpawnMob", "SpawnPlayer", "SpawnExperienceOrb",
    "EntityRelativeMove", "EntityTeleport", "EntityVelocity", "DestroyEntities",
    "decode_spawn_object", "decode_spawn_mob", "decode_spawn_player",
    "decode_spawn_experience_orb", "decode_entity_relative_move",
    "decode_entity_teleport", "decode_entity_velocity", "decode_destroy_entities",
]
