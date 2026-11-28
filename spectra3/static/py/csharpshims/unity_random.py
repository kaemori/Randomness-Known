from functools import reduce

import numpy as np


def xs_next(state):
    s0, s1, s2, s3 = state
    value = (s0 ^ ((s0 << 11) & 0xFFFFFFFF)) & 0xFFFFFFFF
    value = (value ^ (value >> 8)) & 0xFFFFFFFF
    value = (value ^ s3 ^ (s3 >> 19)) & 0xFFFFFFFF
    return (s1, s2, s3, value), value


def xs_value(state):
    state, value = xs_next(state)
    return state, np.float32((value & 0x7FFFFF) / 0x7FFFFF)


def xs_range_float(state, minimum, maximum):
    minimum, maximum = min(minimum, maximum), max(minimum, maximum)
    state, value = xs_value(state)
    return state, minimum + value * (maximum - minimum)


def xs_range_int(state, minimum, maximum):
    minimum, maximum = min(minimum, maximum), max(minimum, maximum)
    state, value = xs_value(state)
    span = maximum - minimum
    return state, minimum if span == 0 else minimum + int(value * span)


def xs_range_ambig(state, minimum, maximum):
    if isinstance(minimum, int) and isinstance(maximum, int):
        return xs_range_int(state, minimum, maximum)
    return xs_range_float(state, minimum, maximum)


def splitmix64(seed):
    def str_to_seed(value):
        return reduce(lambda acc, char: (acc * 31 + ord(char)) & 0xFFFFFFFFFFFFFFFF, value, 0)

    def next_value(value):
        value = (value + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return value ^ (value >> 31)

    value = str_to_seed(seed) if isinstance(seed, str) else seed & 0xFFFFFFFFFFFFFFFF
    result = []
    for _ in range(4):
        value = next_value(value)
        result.append(value & 0xFFFFFFFF)
    return result
