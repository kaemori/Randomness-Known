from dataclasses import dataclass
import numpy as np
import math
from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
    CellularDistanceFunction,
    CellularReturnType,
)


from cparser.ir_nodes import *
from tools.unity_random import UnityRandom
from tools.vectors import Vector2, Vector3


@dataclass
class RunSettings:
    # pretty misleading name for something that just stores run settings
    settings: dict

    def GetRunSettingFloat(self, query):
        return self.settings[query]


@dataclass
class GenerationSettings:
    biomeDepth: int
    width: int
    height: int
    chunkWidth: int
    chunkHeight: int
    run_settings: RunSettings
    Random: UnityRandom
    deferred_gen_block_cirle: Any
    deferred_gen_ore_fn: Any
    deferred_gen_liquid: Any
    deferred_gen_structures: Any

    def __post_init__(self):
        self.worldBlocks = np.zeros((self.width, self.height), dtype=np.uint16)
        self.fluid = np.zeros((self.width, self.height), dtype=np.uint8)

        class Mathf:
            # highkey just monkeypatch it
            @staticmethod
            def RoundToInt(x):
                return round(x)

            @staticmethod
            def Clamp(a, mi, ma):
                return max(mi, min(a, ma))

            @staticmethod
            def Lerp(a, b, t):
                return a + (b - a) * t

        self.Mathf = Mathf

    def WorldToBlockPos(self, pos):
        return pos + Vector2(self.width // 2, self.height // 2)

    def SetBlock(self, vector2int, block):
        self.worldBlocks[*vector2int] = block

    @property
    def to_global_dict(self):
        return {
            "math": math,
            "Mathf": self.Mathf,
            "FastNoiseLite": FastNoiseLite,
            "NoiseType": NoiseType,
            "FractalType": FractalType,
            "CellularDistanceFunction": CellularDistanceFunction,
            "CellularReturnType": CellularReturnType,
            "WorldGeneration": self.run_settings,
            "biomeDepth": self.biomeDepth,
            "width": self.width,
            "height": self.height,
            "halfHeight": self.height // 2,
            "chunkWidth": self.chunkWidth,
            "chunkHeight": self.chunkHeight,
            "Random": self.Random,
            "Vector2": Vector2,
            "Vector3": Vector3,
            "GenerateBlockCircle": self.deferred_gen_block_cirle,
            "WorldToBlockPos": self.WorldToBlockPos,
            "worldBlocks": self.worldBlocks,
            "GenerateOres": self.deferred_gen_ore_fn,
            "UpdateWorld": lambda: print("update world called"),
            "WorldGenerateStructures": self.deferred_gen_structures,
            "PlaceLiquids": self.deferred_gen_liquid,
        }
