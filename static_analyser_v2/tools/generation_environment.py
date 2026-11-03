import math
from functools import partial

from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.unity_shim import Mathf, make_unity_engine
from tools.vectors import Vector2, Vector3


def SetLoadingText(env, word):
    print(f"SLT: {word}")


def WorldGenerateStructures(env):
    print("world generate structures!")


def GenerateDropCapsules(env, _):
    pass


def GenerateCollapsedPods(env, _):
    pass


def GenerateBlockCircle(env, *args):
    pass


def GenerateOres(env):
    print("generate ores!")


def UpdateWorld(env):
    print("update world!")


def PlaceLiquids(env, perchunk, type, maxfill):
    print("PlaceLiquids")


def WorldToBlockPos(pos):
    return pos + (512, 512)


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
        "Vector2",
        "Vector2Int",
        "Vector3Int",
        "biomeOverride",
        "OverrideSceneType",
        "GetRunSettingFloat",
        "SetLoadingText",
        "WorldGenerateStructures",
        "GenerateDropCapsules",
        "GenerateCollapsedPods",
        "GenerateBlockCircle",
        "GenerateOres",
        "UpdateWorld",
        "PlaceLiquids",
        "WorldToBlockPos",
    )
    __slots__ = _NAMES + ("as_dict",)

    def __init__(
        self,
        world_state,
        slt_fn=None,
        wgs_fn=None,
        gdc_fn=None,
        gcp_fn=None,
        gbc_fn=None,
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
        self.Vector2 = Vector2
        self.Vector2Int = Vector2
        self.Vector3Int = Vector3
        self.biomeOverride = ws.biome_override
        self.OverrideSceneType = ws.override_scene_type

        self.GetRunSettingFloat = world_state.run_settings.GetRunSettingFloat

        self.SetLoadingText = partial(slt_fn or SetLoadingText, self)
        self.WorldGenerateStructures = partial(wgs_fn or WorldGenerateStructures, self)
        self.GenerateDropCapsules = partial(gdc_fn or GenerateDropCapsules, self)
        self.GenerateCollapsedPods = partial(gcp_fn or GenerateCollapsedPods, self)
        self.GenerateBlockCircle = partial(gbc_fn or GenerateBlockCircle, self)
        self.GenerateOres = partial(go_fn or GenerateOres, self)
        self.UpdateWorld = partial(uw_fn or UpdateWorld, self)
        self.PlaceLiquids = partial(pl_fn or PlaceLiquids, self)

        self.WorldToBlockPos = WorldToBlockPos

        self.as_dict = {n: getattr(self, n) for n in self._NAMES}
