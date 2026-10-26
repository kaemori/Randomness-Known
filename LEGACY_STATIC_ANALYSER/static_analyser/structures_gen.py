from dataclasses import dataclass
import numpy as np
import regex
import math

from tools.context import WorldgenContext
from tools.generation_settings import GenerationSettings, RunSettings
from raycast_tools import Raycaster
from worldgen_tools import get_guid_to_blockid, get_id_image_mapping
from cparser.ir_nodes import *
from tools.unity_random import UnityRandom
from tools.zerodiv import *
from tools.vectors import Vector2, Vector3
from tools.runsettings_parser import run_setting
from structure_tools import _get_single_prefab


# thank you moffsoniks
def exec_safe(code_str, env):
    tree = ast.parse(code_str, mode="exec")
    tree = CSharpDivTransform().visit(tree)
    ast.fix_missing_locations(tree)
    env = {**env, "__csharp_div__": csharp_div}
    exec(compile(tree, "<transpiled>", "exec"), env)
    return env


# raycasting
@dataclass
class RaycastHit2D:
    point: Vector2
    distance: float
    cell: tuple

    def __post_init__(self):
        print("raycast", self.point)

    def __bool__(self):
        return True


@dataclass
class Physics2D:
    raycaster: Raycaster

    def Raycast(self, origin, direction, max_distance, _):
        result = self.raycaster.raycast(origin, direction, max_distance)
        if result is None:
            return None
        hit_point, dist, cell = result
        return RaycastHit2D(point=hit_point, distance=dist, cell=cell)


# resources.load
@dataclass
class Resources:
    class Load(str):
        __slots__ = ()
        __getattr__ = lambda i, _: i
        __call__ = lambda i, *a, **k: i


class Plaything:
    __slots__ = ()
    pt_mocker = lambda *a, **k: a[0]
    __iter__ = __setattr__ = __getattr__ = __getitem__ = __setitem__ = __call__ = (
        pt_mocker
    )


def _spawn_children(gensettings, name, point):
    place_prefab(
        gensettings,
        str(name),
        int(point[0] + gensettings.width // 2),
        int(point[1] + gensettings.height // 2),
        place_tiles=False,
    )


# object.instantiate
@dataclass
class Quaternion:
    identity = [0, 0, 0]

    @staticmethod
    def Euler(x, y, z):
        return z


def GenerateObjectAtPos(
    gensettings: GenerationSettings, pos, name, chance, genmode=False
):
    place_prefab(gensettings, name, int(pos.x), int(pos.y), chance)


def GenerateEntityAtPos(gensettings, pos, baseobj):
    place_prefab(
        gensettings,
        str(baseobj),
        int(pos.x + gensettings.width // 2),
        int(pos.y + gensettings.height // 2),
        place_tiles=False,
    )


def place_prefab(
    gensettings: GenerationSettings,
    name,
    base_x,
    base_y,
    chance=1.0,
    place_tiles=True,
    place_entities=True,
):
    try:
        tilemaps, entities, bounds = _get_single_prefab(name)
    except FileNotFoundError:
        return

    ox, oy = bounds[0] if bounds else (0, 0)
    gensettings.add_debug_cross((ox, oy))

    if place_tiles and tilemaps:
        tilemap = tilemaps[0]
        for x in range(tilemap.shape[0]):
            for y in range(tilemap.shape[1]):
                if gensettings.Random.Range(0.0, 1.0) >= chance:
                    continue
                tile = tilemap[x, y]
                if tile < 0:
                    continue
                world_x, world_y = base_x + ox + x, base_y + oy + y
                if (
                    0 <= world_x < gensettings.width
                    and 0 <= world_y < gensettings.height
                ):
                    gensettings.SetBlock((world_x, world_y), tile)

    if place_entities:
        for entity in entities:
            gensettings.worldBlockEntities.append(
                {
                    **entity,
                    "position": {
                        "x": base_x + ox + entity["position"]["x"],
                        "y": base_y + oy + entity["position"]["y"],
                    },
                }
            )


def GenerateDropCapsules(amt, context: WorldgenContext, env):
    print("generating dropcaps")
    dropcap_py = context.transpiler.get_python_code("GenerateDropCapsules")
    dropcap_py = dropcap_py.replace("this.", "")
    dropcap_py = dropcap_py.replace(
        ".GetComponent<AudioSource>().pitch = Random.Range(0.9, 1.1)",
        "; Random._next()",
    )  # why does this even have a sound when spawned
    dropcap_py = dropcap_py.replace('LayerMask.GetMask(string[] { "Ground" })', "None")
    with open("dropcap.tmp", "w") as f:
        print(dropcap_py, file=f)
    exec(dropcap_py, env | {"amt": amt})


def GenerateCollapsedPods(amt, context: WorldgenContext, env):
    print("generating collpods")
    collpod_py = context.transpiler.get_python_code("GenerateCollapsedPods")
    collpod_py = collpod_py.replace("this.", "")
    collpod_py = regex.sub(r"<.*?>", "", collpod_py)
    collpod_py = collpod_py.replace('LayerMask.GetMask(string[] { "Ground" })', "None")

    collpod_py = collpod_py.replace(
        "component.rounds = Mathf.RoundToInt(component.maxRounds * Random.value)",
        "Random._next()",  # determines mag ammo
    )
    magazine_types = ("boxof12gauge", "smallmagazine", "riflemagazine")
    collpod_py = collpod_py.replace(
        "spawnableMagazines.PickRandom()", "magazine_types[Random.Range(0, 3)]"
    )
    collpod_py = collpod_py.replace(" as GameObject", "")
    collpod_py = collpod_py.replace(
        "component = (Object.Instantiate(Resources.Load(magazine_types[Random.Range(0, 3)]), point, Quaternion.Euler(0.0, 0.0, Random.value * 360.0))).GetComponent()",
        "Object.Instantiate(Resources.Load(magazine_types[Random.Range(0, 3)]), point, Quaternion.Euler(0.0, 0.0, Random.value * 360.0))",
    )

    with open("collpod_py.tmp", "w") as f:
        print(collpod_py, file=f)
    exec_safe(collpod_py, env | {"amt": amt, "magazine_types": magazine_types})


def GenerateLifePods(amt, context: WorldgenContext, env):
    print("generating lifepods")
    lifepod_py = context.transpiler.get_python_code("GenerateLifePods")
    lifepod_py = lifepod_py.replace("this.", "")
    lifepod_py = regex.sub(r"<.*?>", "", lifepod_py)
    lifepod_py = lifepod_py.replace('LayerMask.GetMask(string[] { "Ground" })', "None")
    lifepod_py = lifepod_py.replace(" as GameObject", "")

    # following code disables traders
    lifepod_py = lifepod_py.replace(
        'WorldGeneration.GetRunSettingFloat("traderchance")', "0"
    )

    with open("lifepod_py.tmp", "w") as f:
        print(lifepod_py, file=f)
    exec_safe(lifepod_py, env | {"amt": amt})


def world_generate_structures(
    gensettings: GenerationSettings, context: WorldgenContext
):
    noscale = {"x": 1, "y": 1, "z": 1}

    class RangeF:
        def __init__(self, minn: float, maxx: float):
            self.min = minn
            self.max = maxx

        def RandomFromRange(self) -> float:
            return gensettings.Random.range_float(self.min, self.max)

        def __add__(self, other):
            if isinstance(other, RangeF):
                return RangeF(
                    self.min / other.min, self.max / other.max
                )  # source does division for some reason
            return RangeF(self.min + other, self.max + other)

        def __sub__(self, other):
            if isinstance(other, RangeF):
                return RangeF(self.min - other.min, self.max - other.max)
            return RangeF(self.min - other, self.max - other)

        def __mul__(self, other: float):
            return RangeF(self.min * other, self.max * other)

        def __truediv__(self, other: float):
            return RangeF(self.min / other, self.max / other)

        def __repr__(self):
            return f"RangeF(min={self.min}, max={self.max})"

    @dataclass
    class Object:
        @staticmethod
        def Instantiate(name, point, rot):
            # print(f"{name} at {point} using {rot}")
            gensettings.EntityInstantiate(name, name, point, noscale, rot)
            _spawn_children(gensettings, name, point)

    @dataclass
    class Utils:
        @staticmethod
        def Create(name, point, rot):
            gensettings.EntityInstantiate(name, name, point, noscale, rot)
            _spawn_children(gensettings, name, point)
            return Plaything()  # consumes addcomponent

    print("generating structures,")

    python_file = context.transpiler.get_python_code(
        "WorldGenerateStructures", danger_make_returns_sysexit=True
    )
    python_file = python_file.replace("this.", "")
    python_file = regex.sub(r"<.*?>", "", python_file)

    python_file = python_file.replace(
        'LayerMask.GetMask(string[] { "Ground" })', "None"
    )
    # python_file = python_file.replace("this.", "")

    raycaster = Raycaster(gensettings)
    run_settings_as_dict = gensettings.run_settings.settings
    totalLootRarity = run_settings_as_dict["baselootdensity"] * (
        run_settings_as_dict["lootmultiplier"] ** gensettings.biomeDepth
    )

    with open("temp_genstruct.py", "w") as f:
        f.writelines(python_file)

    env_globals = gensettings.to_global_dict
    env_globals["Physics2D"] = Physics2D(raycaster)
    env_globals["Resources"] = Resources
    env_globals["Quaternion"] = Quaternion
    env_globals["Object"] = Object
    env_globals["RangeF"] = RangeF
    env_globals["Utils"] = Utils
    env_globals["Plaything"] = Plaything
    env_globals["totalLootRarity"] = totalLootRarity
    env_globals["GenerateDropCapsules"] = lambda amt: GenerateDropCapsules(
        amt, context, env_globals
    )
    env_globals["GenerateCollapsedPods"] = lambda amt: GenerateCollapsedPods(
        amt, context, env_globals
    )
    env_globals["GenerateLifePods"] = lambda amt: GenerateLifePods(
        amt, context, env_globals
    )
    env_globals["GenerateObjectAtPos"] = lambda *args, **kwargs: GenerateObjectAtPos(
        gensettings, *args, **kwargs
    )
    env_globals["GenerateEntityAtPos"] = lambda *args, **kwargs: GenerateEntityAtPos(
        gensettings, *args, **kwargs
    )

    # GenerateDropCapsules(gensettings, 0.2, context, env_globals)
    exec(python_file, env_globals)
