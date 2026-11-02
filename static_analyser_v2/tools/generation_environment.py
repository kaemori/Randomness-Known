import math
from functools import partial

from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.unity_shim import Mathf, Plaything, make_unity_engine
from tools.vectors import Vector2, Vector3


def SetLoadingText(env, word):
    print(f"SLT: {word}")


def GenerateOres(env):
    print("generate ores!")
    return Plaything()


def UpdateWorld(env):
    print("update world!")
    return Plaything()


def PlaceLiquids(env, perchunk, type, maxfill):
    print("PlaceLiquids")
    return Plaything()


class Environment:
    _NAMES = (
        "fillnet",
        "fillstart",
        "fillorder",
        "groundy",
        "biomeDepth",
        "width",
        "height",
        "chunkWidth",
        "chunkHeight",
        "Random",
        "WorldGeneration",
        "halfWidth",
        "halfHeight",
        "worldBlocks",
        "fluid",
        "UnityEngine",
        "math",
        "Mathf",
        "FastNoiseLite",
        "Vector2Int",
        "Vector3Int",
        "biomeOverride",
        "OverrideSceneType",
        "GetRunSettingFloat",
        "SetLoadingText",
        "GenerateOres",
        "UpdateWorld",
        "PlaceLiquids",
    )
    __slots__ = _NAMES + ("as_dict",)

    def __init__(
        self,
        world_state,
        slt_fn=None,
        go_fn=None,
        uw_fn=None,
        pl_fn=None,
    ):
        ws = world_state
        self.fillnet = None
        self.fillstart = None
        self.fillorder = None
        self.groundy = None

        self.biomeDepth = ws.biome_depth
        self.width = ws.width
        self.height = ws.height
        self.chunkWidth = ws.chunk_width
        self.chunkHeight = ws.chunk_height
        self.Random = ws.random
        self.WorldGeneration = ws.run_settings
        self.halfWidth = ws.half_width
        self.halfHeight = ws.half_height
        self.worldBlocks = ws.world_blocks
        self.fluid = ws.fluid
        self.UnityEngine = make_unity_engine(ws.random)
        self.math = math
        self.Mathf = Mathf
        self.FastNoiseLite = FastNoiseLite
        self.Vector2Int = Vector2
        self.Vector3Int = Vector3
        self.biomeOverride = ws.biome_override
        self.OverrideSceneType = ws.override_scene_type

        self.GetRunSettingFloat = world_state.run_settings.GetRunSettingFloat

        self.SetLoadingText = partial(slt_fn or SetLoadingText, self)
        self.GenerateOres = partial(go_fn or GenerateOres, self)
        self.UpdateWorld = partial(uw_fn or UpdateWorld, self)
        self.PlaceLiquids = partial(pl_fn or PlaceLiquids, self)

        self.as_dict = {n: getattr(self, n) for n in self._NAMES}
