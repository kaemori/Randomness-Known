from pathlib import Path
from dataclasses import dataclass
from functools import cache
import numpy as np

import irtopython
from tools.generation_settings import GenerationSettings, RunSettings
from raycast_tools import Raycaster
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

# note to self: i dont like how this "module" has non-main init code. might be better if i turned this into a class
# lets not scope creep

# note to self: a lot of modules makes their own ALL_MODULES.
# # if theres a way to have it be inited in the main and reused everywhere else,
# thatd be very cool. currently, we have cacheoutput, but it icks me
WORLDGEN_MODULE = "WorldGeneration"
DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)


@cache
def _get_transpiled_fn(fn_name: str):
    entry = EntryPoint(WORLDGEN_MODULE, fn_name)
    line = entry.resolve(MODULE_INDEX)
    body = get_function_body(entry.module, line, ALL_MODULES)
    body = clean_up_function(body)
    ir = transpile(body, fn_name)
    return irtopython.convert_function(ir)


@dataclass
class Physics2D:
    # just to bind it to the c# fn of the same name, Physics2D.Raycast
    raycaster: Raycaster

    def Raycast(self, origin, direction, max_distance, _):
        # source uses some sort of mask?
        return self.raycaster.raycast(origin, direction, max_distance)


def GenerateDropCapsules(gensettings, amt):
    dropcap_py = _get_transpiled_fn("GenerateBlockCircle")


def GenerateCollapsedPods(gensettings, amt): ...


def GenerateBlockCircle(
    gensettings,
    pos,
    size,
    block,
    chance,
    chanceEnd,
    autoUpdateChunk=False,
    force=False,
    ignoreInfinityck=False,
): ...


def world_generate_structures(gensettings: GenerationSettings):
    print("generating structures,")

    struct_entry = EntryPoint(WORLDGEN_MODULE, "WorldGenerateStructures")
    struct_entry_line = struct_entry.resolve(MODULE_INDEX)
    struct_function_body = get_function_body(
        struct_entry.module, struct_entry_line, ALL_MODULES
    )
    struct_function_body = clean_up_function(struct_function_body)
    python_file = irtopython.convert_function(
        transpile(struct_function_body, "WorldGenerateStructures"),
        danger_make_returns_sysexit=True,
    )
    python_file = python_file.replace("this.", "")

    raycaster = Raycaster(gensettings)
    run_settings_as_dict = gensettings.run_settings.settings
    totalLootRarity = run_settings_as_dict["baselootdensity"] * (
        run_settings_as_dict["lootmultiplier"] ** gensettings.biomeDepth
    )

    with open("temp_genstruct.py", "w") as f:
        f.writelines(python_file)

    env_globals = gensettings.to_global_dict
    env_globals["totalLootRarity"] = totalLootRarity
    env_globals["GenerateDropCapsules"] = GenerateDropCapsules
    env_globals["GenerateCollapsedPods"] = GenerateCollapsedPods
    env_globals["Physics2D"] = Physics2D(raycaster)
