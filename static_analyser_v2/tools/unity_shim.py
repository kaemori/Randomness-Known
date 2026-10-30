from tools.vectors import Vector2, Vector3


class Plaything:
    __slots__ = ()

    def _mock(self, *args, **kwargs):
        return self

    __iter__ = __setattr__ = __getattr__ = __getitem__ = __setitem__ = __call__ = _mock


class Mathf:
    @staticmethod
    def RoundToInt(x):
        return round(x)

    @staticmethod
    def Clamp(a, mi, ma):
        return max(mi, min(a, ma))

    @staticmethod
    def Lerp(a, b, t):
        return a + (b - a) * t


class Object:
    # UnityEngine.Object
    @staticmethod
    def Instantiate(who, where, whichdirectiongoddamn):
        print(f"{who} instantiated at {where} facing {whichdirectiongoddamn}")


class UnityEngine:
    __slots__ = ("Random", "Mathf", "Object", "Vector2", "Vector3")

    def __init__(self, random):
        self.Random = random
        self.Mathf = Mathf
        self.Object = Object
        self.Vector2 = Vector2
        self.Vector3 = Vector3


def make_unity_engine(random):
    return UnityEngine(random)
