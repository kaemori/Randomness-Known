from pyfastnoiselite_binded import FastNoiseLite
import pyfastnoiselite.pyfastnoiselite
from collections.abc import Iterable
from functools import reduce
import struct
import time


def to_f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


MASK = 0xFFFFFFFF


class UnityRandom:
    def __init__(self, s0_or_iter, s1=None, s2=None, s3=None):
        self._count = 0
        if isinstance(s0_or_iter, Iterable):
            self.s0, self.s1, self.s2, self.s3 = s0_or_iter
        else:
            self.s0 = s0_or_iter & MASK
            self.s1 = s1 & MASK
            self.s2 = s2 & MASK
            self.s3 = s3 & MASK

    @staticmethod
    def _splitmix64(seed: int):
        def str_to_seed(s: str, base: int = 31, mod: int = 2**64) -> int:
            return reduce(lambda acc, c: (acc * base + ord(c)) % mod, s, 0)

        def next_val(z):
            z = (z + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
            return z ^ (z >> 31)

        seed = str_to_seed(seed) if isinstance(seed, str) else seed
        z = seed & 0xFFFFFFFFFFFFFFFF
        vals = []
        for _ in range(4):
            z = next_val(z)
            vals.append(z & 0xFFFFFFFF)
        return vals

    @staticmethod
    def xorshift128(s0, s1, s2, s3):
        t = s0
        t = (t ^ (t << 11)) & MASK
        t = (t ^ (t >> 8)) & MASK
        t = (t ^ s3 ^ (s3 >> 19)) & MASK
        return s1, s2, s3, t

    @classmethod
    def splitmixed(cls, seedstring):
        return cls(cls._splitmix64(seedstring))

    def _next(self):
        self._count += 1
        t = self.s0
        t = (t ^ (t << 11)) & MASK
        t = (t ^ (t >> 8)) & MASK
        t = (t ^ self.s3 ^ (self.s3 >> 19)) & MASK
        self.s0, self.s1, self.s2, self.s3 = self.s1, self.s2, self.s3, t
        return t

    @property
    def _state(self):
        return (self.s0, self.s1, self.s2, self.s3)

    @property
    def _state_unitylike(self):
        return {f"s{i}": st for i, st in zip(range(4), self._state)}

    # larping
    def _peek(self):
        t = self.s0
        t = (t ^ (t << 11)) & MASK
        t = (t ^ (t >> 8)) & MASK
        t = (t ^ self.s3 ^ (self.s3 >> 19)) & MASK
        return to_f32((t & 0x7FFFFF) / 0x7FFFFF)

    @property
    def value(self):
        return to_f32((self._next() & 0x7FFFFF) / 0x7FFFFF)

    def Range(self, a, b):
        if isinstance(a, float) or isinstance(b, float):
            return self.range_float(a, b)
        return self.range_int(a, b)

    def range_float(self, min_val, max_val):
        return min_val + self.value * (max_val - min_val)

    def range_int(self, min_inclusive, max_exclusive):
        span = max_exclusive - min_inclusive
        if span == 0:
            self._next()
            return min_inclusive
        return min_inclusive + int(self.value * span)


class UnityEngine:
    Random = UnityRandom.splitmixed("nya")


import time
import numpy as np

W = H = 1024
SEED_CAVE, SEED_FREQ = 12345, 67890


def make_cave(freq):
    n = FastNoiseLite(SEED_CAVE)
    n.SetNoiseType(FastNoiseLite.NoiseType.Cellular)
    n.SetFrequency(freq)
    n.SetFractalOctaves(3)
    n.SetFractalType(FastNoiseLite.FractalType.FBm)
    n.SetFractalLacunarity(1.5)
    return n


fm = FastNoiseLite(SEED_FREQ)
fm.SetNoiseType(FastNoiseLite.NoiseType.Perlin)
fm.SetFrequency(0.00037)

t = time.time()
cave = make_cave(0.06)
ref = np.empty((W, H), dtype=np.float32)
for i in range(W):
    for k in range(H):
        cave.SetFrequency(0.06 + fm.GetNoise(i, k) * 0.01)
        ref[i, k] = cave.GetNoise(i, k)
print("loop   :", time.time() - t)

t = time.time()
xs, ys = np.meshgrid(
    np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32), indexing="ij"
)
f = 0.06 + fm.GetNoiseBatch(xs, ys) * 0.01
cave1 = make_cave(1.0)
out = cave1.GetNoiseBatch(xs * f, ys * f)
print("batched:", time.time() - t)

d = np.abs(ref - out)
print("max", d.max(), "p99.99", np.percentile(d, 99.99))
