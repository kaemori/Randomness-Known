from pathlib import Path
import numpy as np
import math

import irtopython

from worldgen_tools import clean_up_function, get_blockinfo
from cparser.transpiler import transpile
from cparser.ir_nodes import *
from tools.index_cache import cache_output
from tools.unity_random import UnityRandom
from helpers.function_getter import (
    EntryPoint,
    load_modules,
    load_module_index,
    get_function_body,
    find_function_lines,
)


def gen_terrain(
    genterr_fn,
    world_blocks,
    blockinfo,
    unityrandom: UnityRandom,
    randcalls=0,
):
    genterr_fn = clean_up_function(genterr_fn)
    ir = transpile(genterr_fn)
    python = irtopython.convert_function(ir).replace("this.", "this_")
    with open("rawr", "w") as f:
        print(python, file=f)


def generate_world(main_function, genterr_fn, blockinfo, unityrandom: UnityRandom):
    chunk_size = 64
    chunk_width = 16
    chunk_height = 16

    width = height = chunk_width * chunk_size  #  1024
    half_width = half_height = width // 2  # 512
    half_chunk_size = chunk_size // 2  # 32

    random_calls = 0
    world_blocks = np.zeros((width, height), dtype=np.uint16)

    for line in main_function:
        match line.strip():
            case "yield return this.WorldCreateBackground();":
                random_calls += math.floor(chunk_width * chunk_height * 0.4) * 4

            case "yield return this.WorldGenerateTerrain();":
                gen_terrain(genterr_fn, world_blocks, blockinfo, unityrandom)


DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)
randstate = [794495536, 2124554959, 1609843594, 2324523346]
unity_random = UnityRandom(randstate)

worldgen_entry = EntryPoint("WorldGeneration", "GenerateWorld")
worldgen_entry_line = worldgen_entry.resolve(MODULE_INDEX)
genterr_entry = EntryPoint("WorldGeneration", "WorldGenerateTerrain")
genterr_entry_line = genterr_entry.resolve(MODULE_INDEX)

genworld_function_body = get_function_body(
    worldgen_entry.module, worldgen_entry_line, ALL_MODULES
)
genterr_function_body = get_function_body(
    genterr_entry.module, genterr_entry_line, ALL_MODULES
)

generate_world(genworld_function_body, genterr_function_body, BLOCKINFO, unity_random)
