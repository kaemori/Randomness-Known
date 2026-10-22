from dataclasses import dataclass
from pathlib import Path
import numpy as np
import regex
import math
import time
import sys
from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
    CellularDistanceFunction,
    CellularReturnType,
)

from worldgen_tools import get_blockinfo, get_id_image_mapping
from worldviewer import show_world
from cparser.ir_nodes import *
from tools.index_cache import cache_output
from tools.unity_random import UnityRandom
from tools.vectors import Vector2, Vector3
from tools.runsettings_parser import run_setting
from tools.context import WorldgenContext
from tools.generation_settings import GenerationSettings, RunSettings
from structures_gen import world_generate_structures
from helpers.function_getter import load_module_index, load_modules
from helpers.transpiler import FunctionTranspiler


def _liquid_flood_fill(gensettings: GenerationSettings, x, y, fill, max_count):
    fill_positions = []
    pending = [(x, y)]
    visited = set()

    while pending:
        current_x, current_y = pending.pop()
        if (
            current_x < 1
            or current_x >= gensettings.width
            or current_y < 1
            or current_y >= gensettings.height
            or (current_x, current_y) in visited
            or gensettings.worldBlocks[current_x, current_y] != 0
            or gensettings.fluid[current_x, current_y] != 0
        ):
            continue

        visited.add((current_x, current_y))
        if len(visited) > max_count:
            continue

        fill_positions.append((current_x, current_y))
        pending.extend(
            (
                (current_x + 1, current_y),
                (current_x - 1, current_y),
                (current_x, current_y - 1),
            )
        )

    if len(visited) <= max_count:
        for fill_x, fill_y in fill_positions:
            gensettings.fluid[fill_x, fill_y] = fill


def gen_liquid(gensettings: GenerationSettings, per_chunk, liquid_type, max_fill):
    amount = gensettings.chunkWidth * gensettings.chunkHeight * per_chunk
    for _ in range(math.ceil(amount)):
        x = int(
            gensettings.Random.Range(-gensettings.width // 2, gensettings.width // 2)
        )
        y = int(
            gensettings.Random.Range(
                -gensettings.height // 2, gensettings.height // 2 - 32
            )
        )
        _liquid_flood_fill(
            gensettings,
            x + gensettings.width // 2,
            y + gensettings.height // 2,
            liquid_type,
            max_fill,
        )


def render_liquid_overlay(img, fluid, tile_size):
    fluid_ids = np.flipud(fluid.T)
    fluid_mask = fluid_ids != 0
    if not fluid_mask.any():
        return img

    liquid_colors = {
        1: (30, 120, 220),
        2: (30, 220, 20),
    }
    alpha = 0.45
    overlay = np.zeros_like(img)
    handled = np.zeros_like(fluid_mask)

    for liquid_id, color in liquid_colors.items():
        m = fluid_ids == liquid_id
        if not m.any():
            continue
        handled |= m
        tile_m = np.repeat(np.repeat(m, tile_size, axis=0), tile_size, axis=1)
        overlay[tile_m] = color

    leftover = fluid_mask & ~handled
    if leftover.any():
        tile_m = np.repeat(np.repeat(leftover, tile_size, axis=0), tile_size, axis=1)
        overlay[tile_m] = (0, 200, 200)

    tile_mask = np.repeat(np.repeat(fluid_mask, tile_size, axis=0), tile_size, axis=1)
    img[tile_mask] = img[tile_mask] * (1 - alpha) + overlay[tile_mask] * alpha

    return img


def gen_ores(python, gensettings: GenerationSettings):
    print("generate ores called!")
    try:
        exec(python, gensettings.to_global_dict)
    except SystemExit:
        pass


def gen_terrain(python, gensettings: GenerationSettings):
    print("generating terrain")
    python = python.replace(
        'Object.Instantiate(Resources.Load("Special/marbleBackground"), BlockToWorldPos(new Vector2Int(j, num18)), Quaternion.Euler(0.0, 0.0, Random.value * 360.0))',
        "Random._next()",
    )
    exec(python, gensettings.to_global_dict)


def gen_block_circle(python, gensettings: GenerationSettings, *args, **kwargs):
    pos, size, block, chance, chanceEnd = args
    autoUpdateChunk = kwargs.get("autoUpdateChunk", False)
    force = kwargs.get("force", False)
    ignoreInfinirock = kwargs.get("ignoreInfinirock", False)

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

    exec(python, env)

    # with open("blockcircle.tmp", "w") as f:
    #     print(python, file=f)


def generate_world(
    run_settings,
    context: WorldgenContext,
    unityrandom: UnityRandom,
):
    main_function = context.transpiler.get_function_body("GenerateWorld")

    genterr_python = context.transpiler.get_python_code(
        "WorldGenerateTerrain", thisless=True
    )
    genore_python = context.transpiler.get_python_code(
        "GenerateOres", danger_make_returns_sysexit=True, thisless=True
    )
    gen_blockcircle_python = context.transpiler.get_python_code(
        "GenerateBlockCircle", thisless=True
    )

    start_time = time.time()
    gensettings = GenerationSettings(
        biomeDepth=1 - 1,
        width=1024,
        height=1024,
        chunkWidth=16,
        chunkHeight=16,
        run_settings=run_settings,
        Random=unityrandom,
        deferred_gen_block_cirle=lambda *args, **kwargs: gen_block_circle(
            gen_blockcircle_python, gensettings, *args, **kwargs
        ),
        deferred_gen_ore_fn=lambda: gen_ores(genore_python, gensettings),
        deferred_gen_liquid=lambda per_chunk, liquid_type, max_fill: gen_liquid(
            gensettings, per_chunk, liquid_type, max_fill
        ),
        deferred_gen_structures=lambda: world_generate_structures(gensettings, context),
    )
    random_calls = 0

    for line in main_function:
        match line.strip():
            case "yield return this.WorldCreateBackground();":
                random_calls += (
                    math.floor(gensettings.chunkWidth * gensettings.chunkHeight * 0.4)
                    * 4
                )

            case "yield return this.WorldGenerateTerrain();":
                gen_terrain(genterr_python, gensettings)

    print(f"took {time.time()-start_time:.2f} to finish!")
    show_world(gensettings, context.blockinfo)


DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)
WORLDGEN_MODULE = "WorldGeneration"
TRANSPILER = FunctionTranspiler(WORLDGEN_MODULE, ALL_MODULES, MODULE_INDEX)
WORLDGEN_CONTEXT = WorldgenContext(
    WORLDGEN_MODULE,
    DECOMPILED_PATH,
    ALL_MODULES,
    MODULE_INDEX,
    BLOCKINFO,
    TRANSPILER,
)
randstate = [794495536, 2124554959, 1609843594, 2324523346]
unity_random = UnityRandom(randstate)

run_settings = RunSettings(
    settings=run_setting(
        "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
    )
)
# run_settings.settings["oreamount"] = 1000.0
# print(run_settings.settings)

generate_world(
    run_settings,
    WORLDGEN_CONTEXT,
    unity_random,
)
