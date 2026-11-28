from functools import reduce
import numba as nb
import numpy as np


@nb.njit(cache=True, inline="always")
def xs_next(state):
    s0, s1, s2, s3 = state
    t = s0
    t = (t ^ (t << 11)) & 0xFFFFFFFF
    t = (t ^ (t >> 8)) & 0xFFFFFFFF
    t = (t ^ s3 ^ (s3 >> 19)) & 0xFFFFFFFF
    return (s1, s2, s3, t), t


@nb.njit(cache=True, inline="always")
def xs_value(state):
    state, t = xs_next(state)
    return state, np.float32((t & 0x7FFFFF) / 0x7FFFFF)


@nb.njit(cache=True, inline="always")
def xs_range_ambig(state, lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    if isinstance(lo, int) and isinstance(hi, int):
        return xs_range_int(state, lo, hi)
    return xs_range_float(state, lo, hi)


@nb.njit(cache=True, inline="always")
def xs_range_float(state, lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    state, v = xs_value(state)
    return state, lo + v * (hi - lo)


@nb.njit(cache=True, inline="always")
def xs_range_int(state, lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    state, v = xs_value(state)
    span = hi - lo
    if span == 0:
        return state, lo
    return state, lo + int(v * span)


def splitmix64(seed: int):
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
