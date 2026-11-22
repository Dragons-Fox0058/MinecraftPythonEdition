"""engine.worldgen.layers — 1.12.2 GenLayer chain for biome assignment."""
from __future__ import annotations
from engine.core import JavaRandom


class GenLayer:
    def __init__(self, base_seed: int, parent=None):
        self.base_seed = base_seed
        self.parent = parent

    def get_ints(self, x, z, w, h) -> list:
        raise NotImplementedError

    def _init_chunk_seed(self, x, z):
        r = JavaRandom(0)
        r.set_seed(self.base_seed)
        rx = r.next_long() // 1
        rz = r.next_long() // 1
        r.set_seed((x * rx + z * rz) ^ self.base_seed)
        return r


class GenLayerIsland(GenLayer):
    def get_ints(self, x, z, w, h):
        out = []
        r = self._init_chunk_seed(x, z)
        for i in range(w * h):
            out.append(1 if r.next_int(10) == 0 else 0)
        return out


class GenLayerZoom(GenLayer):
    def get_ints(self, x, z, w, h):
        ix = x >> 1
        iz = z >> 1
        iw = (w >> 1) + 2
        ih = (h >> 1) + 2
        parent_vals = self.parent.get_ints(ix, iz, iw, ih)
        out_w = iw << 1
        out = [0] * (out_w * (ih << 1))
        for j in range(ih - 1):
            for i in range(iw - 1):
                a = parent_vals[j * iw + i]
                b = parent_vals[j * iw + (i + 1)]
                c = parent_vals[(j + 1) * iw + i]
                d = parent_vals[(j + 1) * iw + (i + 1)]
                r = self._init_chunk_seed(i + ix, j + iz)
                v1 = a; v2 = b; v3 = c; v4 = d
                if a == b and a == c and a == d:
                    v1 = v2 = v3 = v4 = a
                elif a == c and b == d:
                    v1 = v2 = a; v3 = v4 = b
                elif a == b and c == d:
                    v1 = v3 = a; v2 = v4 = c
                else:
                    v1 = a; v2 = b; v3 = c; v4 = d
                    if r.next_int(4) == 0:
                        v1 = a
                    else:
                        v1 = d
                out[(j * 2) * out_w + (i * 2)] = v1
                out[(j * 2) * out_w + (i * 2 + 1)] = v2
                out[((j * 2 + 1)) * out_w + (i * 2)] = v3
                out[((j * 2 + 1)) * out_w + (i * 2 + 1)] = v4
        return out


class GenLayerBiome(GenLayer):
    """Assigns biome IDs using the simplified 1.12.2 rules."""

    def __init__(self, base_seed, parent, biome_provider=None):
        super().__init__(base_seed, parent)
        self.biome_provider = biome_provider

    def get_ints(self, x, z, w, h):
        parent_vals = self.parent.get_ints(x, z, w, h)
        out = []
        r = self._init_chunk_seed(x, z)
        for i in range(w * h):
            out.append(1)  # plains default
        return out
