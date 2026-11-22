"""Minecraft Named Binary Tag (NBT) codec for Java Edition 1.12.2."""
from __future__ import annotations

import gzip
import io
import math
import struct
import zlib
from dataclasses import dataclass
from typing import Any

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

class NBTError(ValueError):
    """Malformed or unsupported NBT data."""

@dataclass(frozen=True)
class NBTList:
    tag_type: int
    values: tuple[Any, ...]

@dataclass(frozen=True)
class NBTDocument:
    name: str
    value: dict[str, Any]


def _read_exact(stream: io.BytesIO, size: int) -> bytes:
    if size < 0:
        raise NBTError("negative read size")
    data = stream.read(size)
    if len(data) != size:
        raise NBTError("unexpected end of NBT data")
    return data

def _unpack(stream: io.BytesIO, fmt: str):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, _read_exact(stream, size))[0]

def _read_string(stream: io.BytesIO) -> str:
    size = _unpack(stream, ">H")
    try:
        return _read_exact(stream, size).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NBTError("invalid UTF-8 NBT string") from exc

def _read_payload(stream: io.BytesIO, tag_type: int, depth: int, max_depth: int):
    if depth > max_depth:
        raise NBTError("NBT nesting limit exceeded")
    if tag_type == TAG_BYTE: return _unpack(stream, ">b")
    if tag_type == TAG_SHORT: return _unpack(stream, ">h")
    if tag_type == TAG_INT: return _unpack(stream, ">i")
    if tag_type == TAG_LONG: return _unpack(stream, ">q")
    if tag_type == TAG_FLOAT: return _unpack(stream, ">f")
    if tag_type == TAG_DOUBLE: return _unpack(stream, ">d")
    if tag_type == TAG_BYTE_ARRAY:
        length = _unpack(stream, ">i")
        if length < 0: raise NBTError("negative byte-array length")
        return _read_exact(stream, length)
    if tag_type == TAG_STRING: return _read_string(stream)
    if tag_type == TAG_LIST:
        child_type = _unpack(stream, ">B")
        length = _unpack(stream, ">i")
        if length < 0 or (child_type == TAG_END and length):
            raise NBTError("invalid NBT list header")
        if child_type > TAG_LONG_ARRAY: raise NBTError("unknown NBT list tag")
        return NBTList(child_type, tuple(
            _read_payload(stream, child_type, depth + 1, max_depth)
            for _ in range(length)
        ))
    if tag_type == TAG_COMPOUND:
        result = {}
        while True:
            child_type = _unpack(stream, ">B")
            if child_type == TAG_END: return result
            if child_type > TAG_LONG_ARRAY: raise NBTError("unknown NBT tag")
            name = _read_string(stream)
            if name in result: raise NBTError(f"duplicate compound key: {name}")
            result[name] = _read_payload(stream, child_type, depth + 1, max_depth)
    if tag_type in (TAG_INT_ARRAY, TAG_LONG_ARRAY):
        length = _unpack(stream, ">i")
        if length < 0: raise NBTError("negative array length")
        fmt = ">i" if tag_type == TAG_INT_ARRAY else ">q"
        return tuple(_unpack(stream, fmt) for _ in range(length))
    raise NBTError(f"unsupported NBT tag type: {tag_type}")

def read_nbt(data: bytes, *, compression: str = "none",
             max_bytes: int = 64 *  1024 * 1024, max_depth: int = 512) -> NBTDocument:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    raw = bytes(data)
    if len(raw) > max_bytes: raise NBTError("NBT input exceeds size limit")
    try:
        if compression == "gzip": raw = gzip.decompress(raw)
        elif compression == "zlib": raw = zlib.decompress(raw)
        elif compression != "none": raise ValueError("compression must be none, gzip, or zlib")
    except (OSError, zlib.error) as exc:
        raise NBTError("invalid compressed NBT data") from exc
    if len(raw) > max_bytes: raise NBTError("decompressed NBT exceeds size limit")
    stream = io.BytesIO(raw)
    root_type = _unpack(stream, ">B")
    if root_type != TAG_COMPOUND: raise NBTError("NBT root must be a compound")
    name = _read_string(stream)
    value = _read_payload(stream, TAG_COMPOUND, 0, max_depth)
    if stream.read(1): raise NBTError("trailing bytes after NBT root")
    return NBTDocument(name, value)

def _encode_string(value: str) -> bytes:
    if not isinstance(value, str): raise TypeError("NBT string must be str")
    data = value.encode("utf-8")
    if len(data) > 65535: raise ValueError("NBT string exceeds 65535 bytes")
    return struct.pack(">H", len(data)) + data

def _infer_tag(value: Any) -> int:
    if isinstance(value, bool): return TAG_BYTE
    if isinstance(value, int):
        if -128 <= value <= 127: return TAG_BYTE
        if -32768 <= value <= 32767: return TAG_SHORT
        if -(1 << 31) <= value < (1 << 31): return TAG_INT
        if -(1 << 63) <= value < (1 << 63): return TAG_LONG
        raise ValueError("integer outside NBT signed long range")
    if isinstance(value, float): return TAG_DOUBLE
    if isinstance(value, str): return TAG_STRING
    if isinstance(value, (bytes, bytearray)): return TAG_BYTE_ARRAY
    if isinstance(value, NBTList): return TAG_LIST
    if isinstance(value, dict): return TAG_COMPOUND
    if isinstance(value, tuple) and all(isinstance(v, int) for v in value):
        return TAG_INT_ARRAY
    raise TypeError(f"cannot infer NBT tag for {type(value).__name__}")

def _write_payload(stream: io.BytesIO, tag_type: int, value: Any, depth: int, max_depth: int):
    if depth > max_depth: raise ValueError("NBT nesting limit exceeded")
    formats = {TAG_BYTE: ">b", TAG_SHORT: ">h", TAG_INT: ">i", TAG_LONG: ">q",
               TAG_FLOAT: ">f", TAG_DOUBLE: ">d"}
    if tag_type in formats:
        stream.write(struct.pack(formats[tag_type], value)); return
    if tag_type == TAG_BYTE_ARRAY:
        data = bytes(value); stream.write(struct.pack(">i", len(data))); stream.write(data); return
    if tag_type == TAG_STRING:
        stream.write(_encode_string(value)); return
    if tag_type == TAG_LIST:
        if not isinstance(value, NBTList): raise TypeError("NBT lists require NBTList")
        stream.write(struct.pack(">Bi", value.tag_type, len(value.values)))
        for item in value.values: _write_payload(stream, value.tag_type, item, depth + 1, max_depth)
        return
    if tag_type == TAG_COMPOUND:
        if not isinstance(value, dict): raise TypeError("NBT compound requires dict")
        for name, child in value.items():
            child_type = _infer_tag(child)
            stream.write(struct.pack(">B", child_type)); stream.write(_encode_string(name))
            _write_payload(stream, child_type, child, depth + 1, max_depth)
        stream.write(b"\x00"); return
    if tag_type in (TAG_INT_ARRAY, TAG_LONG_ARRAY):
        values = tuple(value); fmt = ">i" if tag_type == TAG_INT_ARRAY else ">q"
        stream.write(struct.pack(">i", len(values)))
        for item in values: stream.write(struct.pack(fmt, item))
        return
    raise ValueError(f"unsupported NBT tag type: {tag_type}")

def write_nbt(document: NBTDocument | dict[str, Any], *, name: str = "",
              compression: str = "none", max_depth: int = 512) -> bytes:
    if isinstance(document, NBTDocument):
        name, value = document.name, document.value
    elif isinstance(document, dict): value = document
    else: raise TypeError("document must be NBTDocument or dict")
    stream = io.BytesIO()
    stream.write(b"\x0a"); stream.write(_encode_string(name))
    _write_payload(stream, TAG_COMPOUND, value, 0, max_depth)
    raw = stream.getvalue()
    if compression == "gzip": return gzip.compress(raw, mtime=0)
    if compression == "zlib": return zlib.compress(raw)
    if compression == "none": return raw
    raise ValueError("compression must be none, gzip, or zlib")


__all__ = ["NBTError", "NBTList", "NBTDocument", "read_nbt", "write_nbt",
           "TAG_END", "TAG_BYTE", "TAG_SHORT", "TAG_INT", "TAG_LONG",
           "TAG_FLOAT", "TAG_DOUBLE", "TAG_BYTE_ARRAY", "TAG_STRING",
           "TAG_LIST", "TAG_COMPOUND", "TAG_INT_ARRAY", "TAG_LONG_ARRAY"]
