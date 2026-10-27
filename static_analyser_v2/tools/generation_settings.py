import base64
import gzip
import json
import math
from dataclasses import MISSING, dataclass, field, fields
from functools import wraps
from types import SimpleNamespace


import numpy as np

from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.unity_random import UnityRandom
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
    # UnityEngine Object,
    @staticmethod
    def Instantiate(who, where, whichdirectiongoddamn):
        print(f"{who} instantiated at {where} facing {whichdirectiongoddamn}")


@dataclass
class RunSettings:
    settings: dict

    def GetRunSettingFloat(self, query):
        return self.settings[query]

    @staticmethod
    def from_preset_str(preset):
        raw = json.loads(gzip.decompress(base64.b64decode(preset)))
        return RunSettings({d["Item1"]: d["Item2"] for d in raw})


# qol decorators
def accessible_as(fn=None, *, name=None):
    def decorator(f):
        f._accessible_as = name or f.__name__
        return f

    return decorator(fn) if fn is not None else decorator


def noop(func=None, *, pass_args=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if pass_args:
                f(*args, **kwargs)
            else:
                f(*args[:1])
            return Plaything()

        return wrapper

    return decorator(func) if func is not None else decorator


@dataclass(frozen=True)
class GlobalVal:
    default: object = None
    factory: object = None

    def resolve(self, instance):
        return self.factory(instance) if self.factory else self.default

    def __set_name__(self, owner, name):
        object.__setattr__(self, "_name", name)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        cache = instance.__dict__.setdefault("_global_cache", {})
        if self._name not in cache:
            cache[self._name] = self.resolve(instance)
        return cache[self._name]

    def __set__(self, instance, value):
        instance.__dict__.setdefault("_global_cache", {})[self._name] = value


def global_val(default=None, *, factory=None):
    return GlobalVal(default, factory)


def global_field(**kwargs):
    return field(metadata={"global": True}, **kwargs)


@dataclass
class GenerationSettings:
    biomeDepth: int = global_field()
    width: int = global_field()
    height: int = global_field()
    chunkWidth: int = global_field()
    chunkHeight: int = global_field()
    run_settings: RunSettings = field()
    Random: UnityRandom = global_field()
    UnityEngine = global_val(
        factory=lambda s: SimpleNamespace(
            Random=s.Random,
            Mathf=Mathf,
            Object=Object,
            Vector2=Vector2,
            Vector3=Vector3,
        )
    )

    math = global_val(math)
    Mathf = global_val(Mathf)
    FastNoiseLite = global_val(FastNoiseLite)
    Vector2Int = global_val(Vector2)
    Vector3Int = global_val(Vector3)

    WorldGeneration = global_val(factory=lambda s: s.run_settings)
    halfWidth = global_val(factory=lambda s: s.width / 2)
    halfHeight = global_val(factory=lambda s: s.height / 2)
    worldBlocks = global_val(
        factory=lambda s: np.zeros((s.width, s.height), dtype=np.uint16)
    )
    fluid = global_val(factory=lambda s: np.zeros((s.width, s.height), dtype=np.uint8))

    # WorldGenerateTerrain
    biomeOverride = global_val(float("nan"))
    OverrideSceneType = global_val(Plaything())

    @accessible_as
    def SetLoadingText(self, word):
        print(f"SLT: {word}")

    @accessible_as
    @noop
    def GenerateOres(self):
        print("generate ores!")

    @accessible_as
    @noop
    def UpdateWorld(self):
        print("update world!")

    @accessible_as
    @noop(pass_args=True)
    def PlaceLiquids(self, perchunk, type, maxfill):
        print("PlaceLiquids")

    # generate env
    @property
    def to_global_dict(self):
        env = {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if f.metadata.get("global")
        }

        for cls in reversed(type(self).__mro__):
            for name, val in vars(cls).items():
                if hasattr(val, "_accessible_as"):
                    env[val._accessible_as] = val.__get__(self, type(self))
                elif isinstance(val, GlobalVal):
                    env[name] = getattr(self, name)

        return env
