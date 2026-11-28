import math

from .vectors import Vector2, Vector3


class Plaything:
    __slots__ = ("point",)

    def __init__(self, point=None):
        self.point = point

    def __bool__(self):
        return self.point is not None

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self


class Math:
    Abs = staticmethod(abs)


class Mathf:
    RoundToInt = staticmethod(round)
    Abs = staticmethod(abs)

    @staticmethod
    def Clamp(value, minimum, maximum):
        return max(minimum, min(value, maximum))

    @staticmethod
    def Lerp(first, second, amount):
        return first + (second - first) * amount

    @staticmethod
    def Sqrt(value):
        return math.sqrt(value)

    @staticmethod
    def FloorToInt(value):
        return math.floor(value)

    @staticmethod
    def CeilToInt(value):
        return math.ceil(value)


class RandomShim:
    def __init__(self, state, range_ambig, range_float, range_int):
        self._state = state
        self._range_ambig = range_ambig
        self._range_float = range_float
        self._range_int = range_int

    def Range(self, minimum, maximum):
        if isinstance(minimum, int) and isinstance(maximum, int):
            self._state[:], value = self._range_int(self._state, minimum, maximum)
        elif isinstance(minimum, float) or isinstance(maximum, float):
            self._state[:], value = self._range_float(
                self._state, minimum, maximum
            )
        else:
            self._state[:], value = self._range_ambig(
                self._state, minimum, maximum
            )
        return value

    @property
    def value(self):
        self._state[:], value = self._range_float(self._state, 0.0, 1.0)
        return value


class _UnityEngine:
    def __init__(self, random):
        self.Mathf = Mathf
        self.Math = Math
        self.Vector2 = Vector2
        self.Vector3 = Vector3
        self.Random = random


def make_unity_engine(random):
    return _UnityEngine(random)
