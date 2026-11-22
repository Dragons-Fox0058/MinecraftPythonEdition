"""Protocol-340 inventory/window packet codecs, preserving item NBT bytes."""
from __future__ import annotations

import struct
from dataclasses import dataclass

from engine.network.codec import PacketBuffer, ProtocolError
from engine.network.play import SERVERBOUND


MAX_NBT_DEPTH = 64
MAX_NBT_ARRAY = 1_000_000


@dataclass(frozen=True)
class WireItemStack:
    item_id: int | None
    count: int = 0
    damage: int = 0
    nbt: bytes = b""

    @property
    def is_empty(self) -> bool:
        return self.item_id is None


EMPTY_SLOT = WireItemStack(None)


@dataclass(frozen=True)
class WindowItems:
    window_id: int
    items: tuple[WireItemStack, ...]


@dataclass(frozen=True)
class SetSlot:
    window_id: int
    slot: int
    item: WireItemStack


@dataclass(frozen=True)
class OpenWindow:
    window_id: int
    window_type: str
    title_json: str
    slot_count: int
    entity_id: int | None = None


@dataclass(frozen=True)
class WindowProperty:
    window_id: int
    property_id: int
    value: int


@dataclass(frozen=True)
class ConfirmTransaction:
    window_id: int
    action_number: int
    accepted: bool


def _read_nbt_payload(buf: PacketBuffer, tag_type: int, depth: int = 0) -> None:
    if depth > MAX_NBT_DEPTH:
        raise ProtocolError("NBT nesting exceeds maximum depth")
    if tag_type == 1:
        buf.read(1)
    elif tag_type == 2:
        buf.read(2)
    elif tag_type in (3, 5):
        buf.read(4)
    elif tag_type in (4, 6):
        buf.read(8)
    elif tag_type in (7, 11, 12):
        length = struct.unpack(">i", buf.read(4))[0]
        if not 0 <= length <= MAX_NBT_ARRAY:
            raise ProtocolError("NBT array length is out of range")
        width = 1 if tag_type == 7 else (4 if tag_type == 11 else 8)
        buf.read(length * width)
    elif tag_type == 8:
        length = struct.unpack(">H", buf.read(2))[0]
        buf.read(length)
    elif tag_type == 9:
        element_type = buf.read(1)[0]
        length = struct.unpack(">i", buf.read(4))[0]
        if not 0 <= length <= MAX_NBT_ARRAY or (element_type == 0 and length):
            raise ProtocolError("invalid NBT list")
        for _ in range(length):
            _read_nbt_payload(buf, element_type, depth + 1)
    elif tag_type == 10:
        while True:
            child_type = buf.read(1)[0]
            if child_type == 0:
                break
            if child_type > 12:
                raise ProtocolError("unknown NBT tag type")
            name_length = struct.unpack(">H", buf.read(2))[0]
            buf.read(name_length)
            _read_nbt_payload(buf, child_type, depth + 1)
    else:
        raise ProtocolError("unknown NBT tag type")


def _read_slot_nbt(buf: PacketBuffer) -> bytes:
    start = buf.offset
    tag_type = buf.read(1)[0]
    if tag_type == 0:
        return b""
    if tag_type != 10:
        raise ProtocolError("item NBT root must be TAG_End or TAG_Compound")
    name_length = struct.unpack(">H", buf.read(2))[0]
    buf.read(name_length)
    _read_nbt_payload(buf, 10)
    return bytes(buf.data[start:buf.offset])


def decode_slot(buf: PacketBuffer) -> WireItemStack:
    item_id = struct.unpack(">h", buf.read(2))[0]
    if item_id == -1:
        return EMPTY_SLOT
    if item_id < 0:
        raise ProtocolError("invalid item ID in Slot")
    count = struct.unpack(">b", buf.read(1))[0]
    damage = struct.unpack(">h", buf.read(2))[0]
    if count <= 0 or damage < 0:
        raise ProtocolError("invalid item count or damage in Slot")
    return WireItemStack(item_id, count, damage, _read_slot_nbt(buf))


def encode_slot(item: WireItemStack) -> bytes:
    if not isinstance(item, WireItemStack):
        raise TypeError("item must be a WireItemStack")
    if item.is_empty:
        return struct.pack(">h", -1)
    if (isinstance(item.item_id, bool) or not isinstance(item.item_id, int)
            or not 0 <= item.item_id <= 32767):
        raise ValueError("wire item ID must be 0..32767")
    if isinstance(item.count, bool) or not isinstance(item.count, int) or not 1 <= item.count <= 127:
        raise ValueError("wire item count must be 1..127")
    if isinstance(item.damage, bool) or not isinstance(item.damage, int) or not 0 <= item.damage <= 32767:
        raise ValueError("wire item damage must be 0..32767")
    if not isinstance(item.nbt, bytes):
        raise TypeError("wire item NBT must be bytes")
    if item.nbt and item.nbt[0] != 10:
        raise ValueError("wire item NBT must be a compound tag")
    return struct.pack(">hb h", item.item_id, item.count, item.damage) + item.nbt


def decode_window_items(payload: bytes) -> WindowItems:
    buf = PacketBuffer(payload)
    window_id = buf.read(1)[0]
    count = struct.unpack(">h", buf.read(2))[0]
    if not 0 <= count <= 1024:
        raise ProtocolError("invalid Window Items slot count")
    items = tuple(decode_slot(buf) for _ in range(count))
    if buf.remaining:
        raise ProtocolError("trailing Window Items payload")
    return WindowItems(window_id, items)


def decode_set_slot(payload: bytes) -> SetSlot:
    buf = PacketBuffer(payload)
    window_id = struct.unpack(">b", buf.read(1))[0]
    slot = struct.unpack(">h", buf.read(2))[0]
    item = decode_slot(buf)
    if buf.remaining:
        raise ProtocolError("trailing Set Slot payload")
    return SetSlot(window_id, slot, item)


def decode_open_window(payload: bytes) -> OpenWindow:
    buf = PacketBuffer(payload)
    window_id = buf.read(1)[0]
    window_type = buf.read_string(max_chars=32)
    title = buf.read_string(max_chars=32767)
    slot_count = buf.read(1)[0]
    entity_id = struct.unpack(">i", buf.read(4))[0] if window_type == "EntityHorse" else None
    if not window_type or buf.remaining:
        raise ProtocolError("invalid Open Window payload")
    return OpenWindow(window_id, window_type, title, slot_count, entity_id)


def decode_close_window(payload: bytes) -> int:
    if len(payload) != 1:
        raise ProtocolError("Close Window payload must be exactly one byte")
    return payload[0]


def decode_window_property(payload: bytes) -> WindowProperty:
    if len(payload) != 5:
        raise ProtocolError("Window Property payload must be exactly five bytes")
    window_id = payload[0]
    property_id, value = struct.unpack(">hh", payload[1:])
    return WindowProperty(window_id, property_id, value)


def decode_confirm_transaction(payload: bytes) -> ConfirmTransaction:
    if len(payload) != 4 or payload[3] not in (0, 1):
        raise ProtocolError("invalid Confirm Transaction payload")
    window_id = struct.unpack(">b", payload[:1])[0]
    action_number = struct.unpack(">h", payload[1:3])[0]
    return ConfirmTransaction(window_id, action_number, bool(payload[3]))


def serverbound_confirm_transaction(window_id: int, action_number: int,
                                    accepted: bool) -> tuple[int, bytes]:
    if isinstance(window_id, bool) or not isinstance(window_id, int) or not -128 <= window_id <= 127:
        raise ValueError("window_id must be a signed byte")
    if isinstance(action_number, bool) or not isinstance(action_number, int) or not -32768 <= action_number <= 32767:
        raise ValueError("action_number must be a signed short")
    if not isinstance(accepted, bool):
        raise TypeError("accepted must be bool")
    return 0x05, struct.pack(">bh?", window_id, action_number, accepted)


def serverbound_close_window(window_id: int) -> tuple[int, bytes]:
    if isinstance(window_id, bool) or not isinstance(window_id, int) or not 0 <= window_id <= 255:
        raise ValueError("window_id must be an unsigned byte")
    return 0x08, bytes((window_id,))


def serverbound_click_window(window_id: int, slot: int, button: int,
                             action_number: int, mode: int,
                             clicked_item: WireItemStack) -> tuple[int, bytes]:
    if isinstance(window_id, bool) or not isinstance(window_id, int) or not 0 <= window_id <= 255:
        raise ValueError("window_id must be an unsigned byte")
    if isinstance(slot, bool) or not isinstance(slot, int) or not -999 <= slot <= 32767:
        raise ValueError("slot must be -999..32767")
    if isinstance(button, bool) or not isinstance(button, int) or not -128 <= button <= 127:
        raise ValueError("button must be a signed byte")
    if isinstance(action_number, bool) or not isinstance(action_number, int) or not -32768 <= action_number <= 32767:
        raise ValueError("action_number must be a signed short")
    if isinstance(mode, bool) or not isinstance(mode, int) or not 0 <= mode <= 6:
        raise ValueError("click mode must be 0..6")
    return 0x07, (
        struct.pack(">Bhbh", window_id, slot, button, action_number)
        + PacketBuffer().to_bytes()
        + _write_varint_bytes(mode)
        + encode_slot(clicked_item)
    )


def _write_varint_bytes(value: int) -> bytes:
    buf = PacketBuffer()
    buf.write_varint(value)
    return buf.to_bytes()


__all__ = [
    "WireItemStack", "EMPTY_SLOT", "WindowItems", "SetSlot", "OpenWindow",
    "WindowProperty", "ConfirmTransaction", "decode_slot", "encode_slot",
    "decode_window_items", "decode_set_slot", "decode_open_window",
    "decode_close_window", "decode_window_property", "decode_confirm_transaction",
    "serverbound_confirm_transaction", "serverbound_close_window",
    "serverbound_click_window",
]
