from pathlib import Path
from dataclasses import dataclass
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

import irtopython

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
    deferred_gen_ore_fn: Any

    def __post_init__(self):
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

        self.Mathf = Mathf

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
            "halfHeight": self.height // 2,
            "chunkWidth": self.chunkWidth,
            "chunkHeight": self.chunkHeight,
            "Random": self.Random,
            "Vector2": Vector2,
            "Vector3": Vector3,
            "worldBlocks": self.worldBlocks,
            "GenerateOres": self.deferred_gen_ore_fn,
            "UpdateWorld": lambda: print("update world called"),
            "WorldGenerateStructures": lambda: print("WorldGenerateStructures called"),
            "PlaceLiquids": lambda per_chunk, liquid_type, max_fill: gen_liquid(
                self, per_chunk, liquid_type, max_fill
            ),
        }


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
        # print(f"liquid at {x}, {y}")
        _liquid_flood_fill(
            gensettings,
            x + gensettings.width // 2,
            y + gensettings.height // 2,
            liquid_type,
            max_fill,
        )


def render_liquid_overlay(img, fluid, tile_size):
    """Composite the fluid grid as a translucent overlay on top of the
    already-rendered terrain image. Returns the (possibly unmodified) img."""
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


def gen_ores(genore_fn, gensettings: GenerationSettings):
    print("generate ores called!")
    genore_fn = clean_up_function(genore_fn)
    ir = transpile(genore_fn, "GenerateOres")
    python = irtopython.convert_function(ir, danger_make_returns_sysexit=True).replace(
        "this.", ""
    )
    with open("ores", "w") as f:
        print(python, file=f)

    try:
        exec(python, gensettings.to_global_dict)
    except SystemExit:
        pass


def gen_terrain(genterr_fn, genore_fn, gensettings: GenerationSettings):
    genterr_fn = clean_up_function(genterr_fn)
    ir = transpile(genterr_fn, "WorldGenerateTerrain")
    python = (
        irtopython.convert_function(ir)
        .replace("this.", "")
        .replace(
            'Object.Instantiate(Resources.Load("Special/marbleBackground"), BlockToWorldPos(new Vector2Int(j, num18)), Quaternion.Euler(0.0, 0.0, Random.value * 360.0))',
            "Random._next()",
        )
    )
    with open("rawr", "w") as f:
        print(python, file=f)
    exec(python, gensettings.to_global_dict)


def generate_world(
    run_settings,
    main_function,
    genterr_fn,
    genore_fn,
    blockinfo,
    unityrandom: UnityRandom,
):
    start_time = time.time()
    gensettings = GenerationSettings(
        biomeDepth=5 - 1,
        width=1024,
        height=1024,
        chunkWidth=16,
        chunkHeight=16,
        run_settings=run_settings,
        Random=unityrandom,
        deferred_gen_ore_fn=lambda: gen_ores(genore_fn, gensettings),
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
                gen_terrain(genterr_fn, genore_fn, gensettings)

    print(f"took {time.time()-start_time:.2f} to finish!")
    # we done!
    import matplotlib.pyplot as plt

    # import matplotlib.colors as mcolors
    import numpy as np

    id_image_mapping = get_id_image_mapping(blockinfo)

    h, w = gensettings.worldBlocks.T.shape
    tile_size = 8
    block_ids = np.flipud(gensettings.worldBlocks.T)
    tile_images = np.zeros(
        (max(blockinfo) + 1, tile_size, tile_size, 3), dtype=np.uint8
    )
    for block_id, tile_image in id_image_mapping.items():
        if isinstance(block_id, int):
            tile_images[block_id] = np.asarray(tile_image)

    img = tile_images[block_ids]
    img = (
        img.transpose(0, 2, 1, 3, 4)
        .reshape(h * tile_size, w * tile_size, 3)
        .astype(np.float32)
    )

    img = render_liquid_overlay(img, gensettings.fluid, tile_size)
    img = img.astype(np.uint8)

    plt.figure(figsize=(16, 16))
    plt.imshow(img, origin="upper", interpolation="nearest")
    plt.show()


DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)
randstate = [794495536, 2124554959, 1609843594, 2324523346]
unity_random = UnityRandom(randstate)

WORLDGEN_MODULE = "WorldGeneration"
worldgen_entry = EntryPoint(WORLDGEN_MODULE, "GenerateWorld")
worldgen_entry_line = worldgen_entry.resolve(MODULE_INDEX)
genterr_entry = EntryPoint(WORLDGEN_MODULE, "WorldGenerateTerrain")
genterr_entry_line = genterr_entry.resolve(MODULE_INDEX)
genore_entry = EntryPoint(WORLDGEN_MODULE, "GenerateOres")
genore_entry_line = genore_entry.resolve(MODULE_INDEX)

run_settings = RunSettings(
    settings=run_setting(
        "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
    )
)
# run_settings.settings["oreamount"] = 1000.0
# print(run_settings.settings)


genworld_function_body = get_function_body(
    worldgen_entry.module, worldgen_entry_line, ALL_MODULES
)
genterr_function_body = get_function_body(
    genterr_entry.module, genterr_entry_line, ALL_MODULES
)
genore_function_body = get_function_body(
    genore_entry.module, genore_entry_line, ALL_MODULES
)

generate_world(
    run_settings,
    genworld_function_body,
    genterr_function_body,
    genore_function_body,
    BLOCKINFO,
    unity_random,
)
