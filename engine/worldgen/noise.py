"""engine.worldgen.noise — 1.12.2 noise generators (Perlin, Octaves, Simplex)."""
from __future__ import annotations
import math
import numpy as np
from engine.core import JavaRandom


class NoiseGeneratorPerlin:
    """1.12.2 NoiseGeneratorImproved (Perlin)."""

    GRAD_X = (1, -1, 1, -1, 1, -1, 1, -1, 0, 0, 0, 0, 1, 0, -1, 0)
    GRAD_Y = (1, -1, -1, 1, 0, 0, 0, 0, 1, -1, 1, -1, 1, -1, -1, 1)
    GRAD_Z = (0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, -1, 0, 1, 0, -1)
    GRAD_2X = (1, -1, 1, -1, 1, -1, 1, -1, 0, 0, 0, 0, 1, 0, -1, 0)
    GRAD_2Z = (0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, -1, 0, 1, 0, -1)

    def __init__(self, rng: JavaRandom):
        self.perm = np.zeros(512, dtype=np.int32)
        self.ox = np.zeros(512, dtype=np.float64)
        self.oy = np.zeros(512, dtype=np.float64)
        self.oz = np.zeros(512, dtype=np.float64)
        for i in range(256):
            self.perm[i] = i
        for i in range(256):
            j = rng.next_int(256 - i) + i
            self.perm[i], self.perm[j] = self.perm[j], self.perm[i]
            self.ox[i] = rng.next_float() * 256.0
            self.oy[i] = rng.next_float() * 256.0
            self.oz[i] = rng.next_float() * 256.0
        for i in range(256, 512):
            self.perm[i] = self.perm[i - 256]
            self.ox[i] = self.ox[i - 256]
            self.oy[i] = self.oy[i - 256]
            self.oz[i] = self.oz[i - 256]
        self.perm = self.perm.astype(np.int32)
        self.ox = self.ox.astype(np.float64)
        self.oy = self.oy.astype(np.float64)
        self.oz = self.oz.astype(np.float64)

    def _pop2(self, x, y):
        return (self.GRAD_2X[(x & 15)] * y) if False else 0.0

    def _grad(self, hash_, x, y, z):
        h = hash_ & 15
        return self.GRAD_X[h]*x + self.GRAD_Y[h]*y + self.GRAD_Z[h]*z

    @staticmethod
    def _lerp(t, a, b):
        return a + t * (b - a)

    @staticmethod
    def _fade(t):
        return t*t*t*(t*(t*6 - 15) + 10)

    def noise3(self, x, y, z) -> float:
        fx = math.floor(x); fy = math.floor(y); fz = math.floor(z)
        xi = int(fx) & 255; yi = int(fy) & 255; zi = int(fz) & 255
        x -= fx; y -= fy; z -= fz
        u = self._fade(x); v = self._fade(y); w = self._fade(z)
        A  = self.perm[xi] + yi
        AA = self.perm[A] + zi
        AB = self.perm[A + 1] + zi
        B  = self.perm[xi + 1] + yi
        BA = self.perm[B] + zi
        BB = self.perm[B + 1] + zi
        x1 = self._lerp(u, self._grad(self.perm[AA],   x,   y,   z),
                            self._grad(self.perm[BA],   x-1, y,   z))
        x2 = self._lerp(u, self._grad(self.perm[AB],   x,   y-1, z),
                            self._grad(self.perm[BB],   x-1, y-1, z))
        y1 = self._lerp(v, x1, x2)
        x3 = self._lerp(u, self._grad(self.perm[AA+1], x,   y,   z-1),
                            self._grad(self.perm[BA+1], x-1, y,   z-1))
        x4 = self._lerp(u, self._grad(self.perm[AB+1], x,   y-1, z-1),
                            self._grad(self.perm[BB+1], x-1, y-1, z-1))
        y2 = self._lerp(v, x3, x4)
        return self._lerp(w, y1, y2)

    def populate_noise_array(self, values, x, y, z, sx, sy, sz, sx_scale, sy_scale, sz_scale):
        out_idx = 0
        if sy == 1:
            for ix in range(sx):
                xx = (x + ix) * sx_scale + self.ox[0]
                for iz in range(sz):
                    zz = (z + iz) * sz_scale + self.oz[0]
                    values[out_idx] = self.noise3(xx, y * sy_scale, zz)
                    out_idx += 1
            return
        for iz in range(sz):
            zz = (z + iz) * sz_scale + self.oz[0]
            for ix in range(sx):
                xx = (x + ix) * sx_scale + self.ox[0]
                for iy in range(sy):
                    yy = (y + iy) * sy_scale + self.oy[0]
                    values[out_idx] = self.noise3(xx, yy, zz)
                    out_idx += 1


class NoiseGeneratorOctaves:
    """1.12.2 NoiseGeneratorOctaves."""

    def __init__(self, rng: JavaRandom, octaves: int):
        self.octaves = octaves
        self.generators = [NoiseGeneratorPerlin(rng) for _ in range(octaves)]

    def noise3(self, x, y, z) -> float:
        result = 0.0
        scale = 1.0
        for g in self.generators:
            result += g.noise3(x * scale, y * scale, z * scale) / scale
            scale /= 2.0
        return result

    def populate_noise_array(self, values, x, y, z, sx, sy, sz, sx_scale, sy_scale, sz_scale):
        for i in range(len(values)):
            values[i] = 0.0
        scale = 1.0
        for g in self.generators:
            g.populate_noise_array(values, x, y, z, sx, sy, sz,
                                   sx_scale * scale, sy_scale * scale, sz_scale * scale)
            scale /= 2.0


class NoiseGeneratorSimplex:
    """1.12.2 NoiseGeneratorSimplex (OpenSimplex-ish 3D)."""

    GRAD3 = ((1,1,0),(-1,1,0),(1,-1,0),(-1,-1,0),
             (1,0,1),(-1,0,1),(1,0,-1),(-1,0,-1),
             (0,1,1),(0,-1,1),(0,1,-1),(0,-1,-1))

    F2 = 0.5 * (math.sqrt(3.0) - 1.0)
    G2 = (3.0 - math.sqrt(3.0)) / 6.0

    def __init__(self, rng: JavaRandom):
        self.perm = np.zeros(512, dtype=np.int32)
        for i in range(256):
            self.perm[i] = i
        for i in range(256):
            j = rng.next_int(256 - i) + i
            self.perm[i], self.perm[j] = self.perm[j], self.perm[i]
        for i in range(256, 512):
            self.perm[i] = self.perm[i - 256]

    def noise2(self, x, y) -> float:
        s = (x + y) * self.F2
        i = math.floor(x + s); j = math.floor(y + s)
        t = (i + j) * self.G2
        X0 = i - t; Y0 = j - t
        x0 = x - X0; y0 = y - Y0
        if x0 > y0:
            i1, j1 = 1, 0
            i2, j2 = 0, 1
        else:
            i1, j1 = 0, 1
            i2, j2 = 1, 0
        x1 = x0 - i1 + self.G2
        y1 = y0 - j1 + self.G2
        x2 = x0 - i2 + 2*self.G2
        y2 = y0 - j2 + 2*self.G2
        ii = int(i) & 255; jj = int(j) & 255
        n = 0.0
        def _g(idx, xv, yv):
            g = self.GRAD3[self.perm[idx] % 12]
            return g[0]*xv + g[1]*yv
        t0 = 0.5 - x0*x0 - y0*y0
        if t0 >= 0:
            t0 *= t0
            n += t0 * t0 * _g(ii + self.perm[jj], x0, y0)
        t1 = 0.5 - x1*x1 - y1*y1
        if t1 >= 0:
            t1 *= t1
            n += t1 * t1 * _g(ii + i1 + self.perm[jj + j1], x1, y1)
        t2 = 0.5 - x2*x2 - y2*y2
        if t2 >= 0:
            t2 *= t2
            n += t2 * t2 * _g(ii + i2 + self.perm[jj + j2], x2, y2)
        return 70.0 * n
