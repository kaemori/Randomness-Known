from pathlib import Path
from dataclasses import dataclass
import regex
import yaml

from worldgen_tools import clean_up_function, get_blockinfo, get_id_image_mapping
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


@dataclass
class Foreground:
    x: int
    y: int
    idx: int


PREFABS_PATH = Path(
    "/home/fern/Documents/casu_decom/ExportedProject/Assets/Resources/structures"
)
DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)


WORLDGEN_MODULE = "WorldGeneration"
genstruct_entry = EntryPoint(WORLDGEN_MODULE, "WorldGenerateStructures")
genstruct_entry_line = genstruct_entry.resolve(MODULE_INDEX)

genstruct_function_body = get_function_body(
    genstruct_entry.module, genstruct_entry_line, ALL_MODULES
)
# print(genstruct_function_body)


def get_structure_set(genstruct_fn):
    structs = regex.compile(r'Resources\.Load<GameObject>\("Structures\/(.*?)"\)')
    return set(structs.findall("".join(genstruct_fn)))


def _get_single_prefab(name):
    filepath = PREFABS_PATH / (name + ".prefab")
    if not filepath.exists():
        raise FileNotFoundError

    with open(filepath) as prefab:
        content = "\n".join(
            line
            for line in prefab.readlines()
            if not line.startswith("%TAG")
            and not line.startswith("%YAML")
            and not regex.match(r"^--- !u!", line)
        )
        fg_tilemap = []
        data = yaml.safe_load(content)
        print(data.keys())
        # for tile in data["Tilemap"]["m_Tiles"]:
        #     first = tile["first"]
        #     second = tile["second"]
        #     fg_tilemap.append(Foreground(first["x"], first["y"], second["m_TileIndex"]))


# print(get_structure_set(genstruct_function_body))
_get_single_prefab("WoodCross")
