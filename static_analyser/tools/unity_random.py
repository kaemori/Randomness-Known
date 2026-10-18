from collections.abc import Iterable
import struct


def to_f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


MASK = 0xFFFFFFFF


class UnityRandom:
    def __init__(self, s0_or_iter, s1=None, s2=None, s3=None):
        if isinstance(s0_or_iter, Iterable):
            self.s0, self.s1, self.s2, self.s3 = s0_or_iter
        else:
            self.s0 = s0_or_iter & MASK
            self.s1 = s1 & MASK
            self.s2 = s2 & MASK
            self.s3 = s3 & MASK

    @staticmethod
    def xorshift128(s0, s1, s2, s3):
        t = s0
        t = (t ^ (t << 11)) & MASK
        t = (t ^ (t >> 8)) & MASK
        t = (t ^ s3 ^ (s3 >> 19)) & MASK
        return s1, s2, s3, t

    def _next(self):
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

    def value(self):
        return to_f32((self._next() & 0x7FFFFF) / 0x7FFFFF)

    def range_float(self, min_val, max_val):
        return min_val + self.value() * (max_val - min_val)

    def range_int(self, min_inclusive, max_exclusive):
        span = max_exclusive - min_inclusive
        if span == 0:
            return min_inclusive
        return min_inclusive + int(self.value() * span)
