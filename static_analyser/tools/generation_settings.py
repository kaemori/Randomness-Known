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


def gen_block_circle(python, gensettings: "GenerationSettings", *args, **kwargs):
    # pos, size, block, chance, chanceEnd = args
    # autoUpdateChunk = kwargs.get("autoUpdateChunk", False)
    # force = kwargs.get("force", False)
    # ignoreInfinirock = kwargs.get("ignoreInfinirock", False)
    pos, size, block, chance, chanceEnd, autoUpdateChunk, force, ignoreInfinirock = args

    env = gensettings.to_global_dict | {
        "pos": pos,
        "size": size,
        "block": block,
        "chance": chance,
        "chanceEnd": chanceEnd,
        "autoUpdateChunk": autoUpdateChunk,
        "force": force,
        "ignoreInfinirock": ignoreInfinirock,
    }

    python = python.replace("!ignoreInfinirock", "(not ignoreInfinirock)")
    with open("blockcircle.tmp", "w") as f:
        print(python, file=f)
    exec(python, env)


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
        self.worldBlockEntities = []
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
        return Vector2(
            int(pos[0] + self.width // 2),
            int(pos[1] + self.height // 2),
        )

    def BlockToWorldPos(self, pos):
        return Vector2(pos.x - (self.width / 2) + 0.5, pos.y - (self.height / 2) + 0.5)

    def EntityInstantiate(self, id, name, pos, scale, rot_deg, length=-1):
        pos = (pos[0] + self.width // 2, pos[1] + self.height // 2)
        self.worldBlockEntities.append(
            {
                "id": id,
                "name": name,
                "position": {"x": pos[0], "y": pos[1]},
                "scale": scale,
                "rotation_deg": rot_deg,
                "length": length,
            }
        )

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
            "halfWidth": self.width / 2,
            "halfHeight": self.height / 2,
            "chunkWidth": self.chunkWidth,
            "chunkHeight": self.chunkHeight,
            "Random": self.Random,
            "Vector2": Vector2,
            "Vector3": Vector3,
            "SetBlock": self.SetBlock,
            "GenerateBlockCircle": self.deferred_gen_block_cirle,
            "WorldToBlockPos": self.WorldToBlockPos,
            "BlockToWorldPos": self.BlockToWorldPos,
            "worldBlocks": self.worldBlocks,
            "GenerateOres": self.deferred_gen_ore_fn,
            "UpdateWorld": lambda: print("update world called"),
            "WorldGenerateStructures": self.deferred_gen_structures,
            "PlaceLiquids": self.deferred_gen_liquid,
        }
