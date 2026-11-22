"""engine.core.java_random — Exact Java Random (LCG) port for 1.12.2 seeds."""

MASK48 = (1 << 48) - 1
MULT   = 0x5DEECE66D
ADD    = 0xB

class JavaRandom:
    """Exact port of java.util.Random. All 1.12.2 worldgen RNG must use this."""

    __slots__ = ('_seed', '_have_next_gaussian', '_next_gaussian')

    def __init__(self, seed: int = 0):
        self._seed = 0
        self.set_seed(seed)

    def set_seed(self, seed: int):
        self._seed = (seed ^ MULT) & MASK48
        self._have_next_gaussian = False
        self._next_gaussian = 0.0

    def _next(self, bits: int) -> int:
        self._seed = (self._seed * MULT + ADD) & MASK48
        return self._seed >> (48 - bits)

    def next_int(self, bound: int = None) -> int:
        if bound is None:
            # java.util.Random.nextInt(): return next(32) as signed int32.
            v = self._next(32)
            return v - (1 << 32) if v >= (1 << 31) else v
        if bound <= 0:
            raise ValueError('bound must be positive')
        if (bound & -bound) == bound:
            return (bound * self._next(31)) >> 31
        while True:
            bits = self._next(31)
            val = bits % bound
            candidate = (bits - val + (bound - 1)) & 0xFFFFFFFF
            if candidate < 0x80000000:
                return val

    def next_long(self) -> int:
        # java.util.Random.nextLong() sign-extends BOTH next(32) int values
        # before combining them. Treating the low half as unsigned breaks
        # the coordinate-seed derivation used by Minecraft world generation.
        hi = self.next_int()
        lo = self.next_int()
        value = (hi << 32) + lo
        value &= 0xFFFFFFFFFFFFFFFF
        return value - (1 << 64) if value >= (1 << 63) else value

    def next_double(self) -> float:
        return ((self._next(26) << 27) + self._next(27)) / float(1 << 53)

    def next_float(self) -> float:
        return self._next(24) / float(1 << 24)

    def next_boolean(self) -> bool:
        return self._next(1) != 0

    def next_gaussian(self) -> float:
        import math
        if self._have_next_gaussian:
            self._have_next_gaussian = False
            return self._next_gaussian
        while True:
            v1 = 2.0 * self.next_double() - 1.0
            v2 = 2.0 * self.next_double() - 1.0
            s = v1 * v1 + v2 * v2
            if 0.0 < s < 1.0:
                multiplier = math.sqrt(-2.0 * math.log(s) / s)
                self._next_gaussian = v2 * multiplier
                self._have_next_gaussian = True
                return v1 * multiplier

def java_string_hash(s: str) -> int:
    """Java String.hashCode() as int32."""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000: h -= 0x100000000
    return h


def string_seed(seed: int, name: str) -> int:
    """Combine a numeric seed with a string label.

    In 1.12.2 the equivalent operation is usually
        seed + (long) String.hashCode(label)
    for structure placement (village/temple/mineshaft). Some systems use
    seed * 31L + hash instead, but for the structures we implement first
    the additive form matches vanilla.
    """
    value = (seed + java_string_hash(name)) & 0xFFFFFFFFFFFFFFFF
    return value - (1 << 64) if value >= (1 << 63) else value
