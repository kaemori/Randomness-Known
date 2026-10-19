from pathlib import Path
from dataclasses import dataclass
import numpy as np
import math
import sys
from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
    CellularDistanceFunction,
    CellularReturnType,
)

import irtopython

from worldgen_tools import clean_up_function, get_blockinfo, get_id_color_mapping
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


@dataclass
class GenerationSettings:
    biomeDepth: int
    width: int
    height: int
    chunkWidth: int
    chunkHeight: int
    Random: UnityRandom

    def __post_init__(self):
        self.worldBlocks = np.zeros((self.width, self.height), dtype=np.uint16)

    @property
    def to_global_dict(self):
        return {
            "math": math,
            "FastNoiseLite": FastNoiseLite,
            "NoiseType": NoiseType,
            "FractalType": FractalType,
            "CellularDistanceFunction": CellularDistanceFunction,
            "CellularReturnType": CellularReturnType,
            "biomeDepth": self.biomeDepth,
            "width": self.width,
            "height": self.height,
            "halfHeight": self.height // 2,
            "chunkWidth": self.chunkWidth,
            "chunkHeight": self.chunkHeight,
            "Random": self.Random,
            "worldBlocks": self.worldBlocks,
            "GenerateOres": lambda: print("generate ores called"),
            "UpdateWorld": lambda: print("update world called"),
            "WorldGenerateStructures": lambda: print("WorldGenerateStructures called"),
            "PlaceLiquids": lambda a, b, c: print(
                f"PlaceLiquids called w/ {a}, {b}, {c}"
            ),
        }


def gen_terrain(genterr_fn, gensettings: GenerationSettings):
    genterr_fn = clean_up_function(genterr_fn)
    ir = transpile(genterr_fn)
    python = (
        irtopython.convert_function(ir)
        .replace("this.", "")
        .replace(
            'Object.Instantiate(Resources.Load("Special/marbleBackground"), BlockToWorldPos((j, num18)), Quaternion.Euler(0.0, 0.0, Random.value * 360.0))',
            "Random._next()",
        )
        .replace(".GetNoise", ".get_noise")
        .replace(".x", "[0]")
        .replace(".y", "[1]")
        .replace(".x", "[0]")
        .replace(".y", "[1]")
    )
    with open("rawr", "w") as f:
        print(python, file=f)
    exec(python, gensettings.to_global_dict)

    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np

    id_color_mapping = get_id_color_mapping()

    h, w = gensettings.worldBlocks.T.shape
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for block_id, color in id_color_mapping.items():
        mask = gensettings.worldBlocks.T == block_id
        img[mask] = color

    plt.figure(figsize=(16, 16))
    plt.imshow(img, origin="upper", interpolation="nearest")
    plt.show()


def generate_world(main_function, genterr_fn, blockinfo, unityrandom: UnityRandom):
    gensettings = GenerationSettings(
        biomeDepth=5 - 1,
        width=1024,
        height=1024,
        chunkWidth=16,
        chunkHeight=16,
        Random=unityrandom,
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
                gen_terrain(genterr_fn, gensettings)


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
