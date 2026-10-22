from pathlib import Path
from dataclasses import dataclass
from types import SimpleNamespace
import numpy as np
import regex
import yaml

from worldgen_tools import (
    clean_up_function,
    get_blockinfo,
    get_guid_to_blockid,
    get_id_image_mapping,
)
from worldviewer import show_world
from cparser.transpiler import transpile
from cparser.ir_nodes import *
from tools.index_cache import cache_output
from tools.unity_random import UnityRandom
from tools.vectors import Vector2, Vector3
from tools.runsettings_parser import run_setting
from helpers.function_getter import (
    EntryPoint,
    load_modules,
    load_module_index,
    get_function_body,
    find_function_lines,
)

RESOURCES_PATH = (
    Path(__file__).parent
    / "CasU-Decompiled"
    / "ExportedProject"
    / "Assets"
    / "Resources"
)

PREFABS_PATH = (
    Path().cwd() / "CasU-Decompiled" / "ExportedProject" / "Assets" / "Resources"
)
DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)
GUID_TO_BLOCKID_LOOKUP = get_guid_to_blockid(RESOURCES_PATH, BLOCKINFO)
WORLDGEN_MODULE = "WorldGeneration"
genstruct_entry = EntryPoint(WORLDGEN_MODULE, "WorldGenerateStructures")
genstruct_entry_line = genstruct_entry.resolve(MODULE_INDEX)

genstruct_function_body = get_function_body(
    genstruct_entry.module, genstruct_entry_line, ALL_MODULES
)


def get_structure_set(genstruct_fn):
    structs = regex.compile(r'Resources\.Load<GameObject>\("(.*?)"\)')
    return set(structs.findall("".join(genstruct_fn)))


def _get_single_prefab(name):
    filepath = PREFABS_PATH / (name + ".prefab")
    if not filepath.exists():
        raise FileNotFoundError

    with open(filepath) as prefab:
        content = "\n".join(
            "---" if regex.match(r"^--- !u!", line) else line
            for line in prefab.readlines()
            if not line.startswith("%TAG") and not line.startswith("%YAML")
        )
        datas = yaml.load_all(content, Loader=yaml.BaseLoader)

    tilemaps_raws = []
    for data in datas:
        if "Tilemap" in data.keys():
            tilemaps_raws.append(data)

    tilemap = []
    for raw in tilemaps_raws:
        try:
            raw = raw["Tilemap"]
            x_low, x_high = None, None
            y_low, y_high = None, None
            tiles = raw["m_Tiles"]
            for tile in tiles:
                loc = tile["first"]
                x, y = int(loc["x"]), int(loc["y"])
                x_low = x if x_low is None else min(x_low, x)
                x_high = x if x_high is None else max(x_high, x)
                y_low = y if y_low is None else min(y_low, y)
                y_high = y if y_high is None else max(y_high, y)

            lookup_guid = raw["m_TileAssetArray"]
            lookup = [
                GUID_TO_BLOCKID_LOOKUP[item["m_Data"].get("guid", "-1")]
                for item in lookup_guid
            ]

            tiles = np.zeros((x_high - x_low + 1, y_high - y_low + 1), dtype=np.uint16)
            for tile in raw["m_Tiles"]:
                loc = tile["first"]
                x, y = int(loc["x"]), int(loc["y"])
                tiles[x - x_low, y - y_low] = lookup[int(tile["second"]["m_TileIndex"])]

            tilemap.append(tiles)

        except:
            continue

    return tilemap


def _render_tilemap(tm):
    to_show = tm
    viewer_data = SimpleNamespace(
        worldBlocks=to_show,
        fluid=np.zeros_like(to_show, dtype=np.uint8),
    )
    show_world(viewer_data, BLOCKINFO)


print(get_structure_set(genstruct_function_body))
# _get_single_prefab("structures/MedicalBuilding")
# _get_single_prefab("structures/BrickLoot")
# _get_single_prefab("structures/SteelThing")
tm = _get_single_prefab("Lifepod")
_render_tilemap(tm[0])
# _get_single_prefab("BioContainer")
