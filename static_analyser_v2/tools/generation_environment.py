import math
from random import choice
from functools import partial

import numpy as np
from gpu_fnl import pyglslfnl
from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.unity_shim import Math, Mathf, make_unity_engine
from tools.unity_random import xs_value, xs_range_ambig, xs_range_float, xs_range_int
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


_circleSpanCache = {}


def _GetCircleSpans(size):
    spans = _circleSpanCache.get(size)
    if spans is not None:
        return spans

    sizeSq = size * size
    spans = []
    dy = -size
    while dy <= size:
        dySq = dy * dy
        if dySq <= sizeSq:
            dx = int(math.sqrt(sizeSq - dySq))
            spans.append((dy, dx))
        dy += 1

    _circleSpanCache[size] = spans
    return spans


def SimpleBlockCircle(env, pos, size, block):
    spans = _GetCircleSpans(size)

    wb = env.worldBlocks

    for dy, dx in spans:
        y = pos.y + dy
        if y < 0 or y > env.height - 1:
            continue

        xStart = pos.x - dx
        if xStart < 0:
            xStart = 0
        xEnd = pos.x + dx
        if xEnd > env.width - 1:
            xEnd = env.width - 1

        x = xStart
        while x <= xEnd:
            wb[x, y] = block
            x += 1


def DrawLine(env, a, b, thickness, block):
    x0 = a.x
    y0 = a.y
    x1 = b.x
    y1 = b.y

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    halfThickness = thickness >> 1
    steep = dx >= dy

    x, y = x0, y0

    while True:
        if steep:
            i = -halfThickness
            while i <= halfThickness:
                yy = y + i
                if 0 <= x < env.width and 0 <= yy < env.height:
                    env.worldBlocks[x, yy] = block
                i += 1
        else:
            j = -halfThickness
            while j <= halfThickness:
                xx = x + j
                if 0 <= xx < env.width and 0 <= y < env.height:
                    env.worldBlocks[xx, y] = block
                j += 1

        if x != x1 or y != y1:
            e2 = err << 1
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            continue
        break


def utils_create(path, pos, dir):
    ...


def DrawEmptyLine(env, a, b, thickness):
    DrawLine(env, a, b, thickness, 0)


def GenerateOres(env):
    print("generate ores!")


def UpdateWorld(env):
    print("update world!")


def PlaceLiquids(env, perchunk, type, maxfill):
    print("PlaceLiquids")


def WorldToBlockPos(pos):
    return pos + (512, 512)


def BlockToWorldPos(pos):
    return pos - (512.5, 512.5)


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
        "xs_state",
        "xs_value",
        "xs_range_ambig",
        "xs_range_float",
        "xs_range_int",
        "WorldGeneration",
        "halfWidth",
        "halfHeight",
        "worldBlocks",
        "worldBuildingEntities"
        "fluid",
        "UnityEngine",
        "random_choice",
        "math",
        "Math",
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
        "SimpleBlockCircle",
        "DrawLine",
        "DrawEmptyLine",
        "GenerateOres",
        "UpdateWorld",
        "PlaceLiquids",
        "WorldToBlockPos",
        "BlockToWorldPos",
        "np",
        "pyglslfnl",
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
        self.WorldGeneration = ws.run_settings
        self.halfWidth = ws.half_width
        self.halfHeight = ws.half_height
        self.worldBlocks = ws.world_blocks
        self.worldBuildingEntities = ws.world_buildingentities
        self.fluid = ws.fluid

        self.xs_state = ws.random_state
        self.xs_value = xs_value
        self.xs_range_ambig = xs_range_ambig
        self.xs_range_float = xs_range_float
        self.xs_range_int = xs_range_int

        self.UnityEngine = make_unity_engine()
        self.random_choice = choice
        self.math = math
        self.Math = Math
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
        self.SimpleBlockCircle = partial(SimpleBlockCircle, self)
        self.DrawLine = partial(DrawLine, self)
        self.DrawEmptyLine = partial(DrawEmptyLine, self)
        self.utils_create = 

        self.GenerateOres = partial(go_fn or GenerateOres, self)
        self.UpdateWorld = partial(uw_fn or UpdateWorld, self)
        self.PlaceLiquids = partial(pl_fn or PlaceLiquids, self)

        self.WorldToBlockPos = WorldToBlockPos
        self.BlockToWorldPos = BlockToWorldPos
        self.np = np
        self.pyglslfnl = pyglslfnl

        self.as_dict = {n: getattr(self, n) for n in self._NAMES}
