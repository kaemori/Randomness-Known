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

from worldgen_tools import clean_up_function, get_blockinfo, get_id_image_mapping
from cparser.transpiler import transpile
from cparser.ir_nodes import *
from tools.index_cache import cache_output
from tools.unity_random import UnityRandom
from tools.runsettings_parser import run_setting
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
    run_settings: dict
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


def gen_ores(genore_fn, gensettings: GenerationSettings):
    genore_fn = clean_up_function(genore_fn)
    ir = transpile(genore_fn, "GenerateOres")
    python = (
        irtopython.convert_function(ir, danger_make_returns_sysexit=True)
        .replace("this.", "")
        .replace(".x", "[0]")
        .replace(".y", "[1]")
        .replace(".x", "[0]")
        .replace(".y", "[1]")
    )


def gen_terrain(genterr_fn, genore_fn, gensettings: GenerationSettings):
    genterr_fn = clean_up_function(genterr_fn)
    ir = transpile(genterr_fn, "WorldGenerateTerrain")
    python = (
        irtopython.convert_function(ir)
        .replace("this.", "")
        .replace(
            'Object.Instantiate(Resources.Load("Special/marbleBackground"), BlockToWorldPos((j, num18)), Quaternion.Euler(0.0, 0.0, Random.value * 360.0))',
            "Random._next()",
        )
        .replace(".x", "[0]")
        .replace(".y", "[1]")
        .replace(".x", "[0]")
        .replace(".y", "[1]")
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
    gensettings = GenerationSettings(
        biomeDepth=5 - 1,
        width=1024,
        height=1024,
        chunkWidth=16,
        chunkHeight=16,
        run_settings=run_settings,
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
                gen_terrain(genterr_fn, genore_fn, gensettings)

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
    img = img.transpose(0, 2, 1, 3, 4).reshape(h * tile_size, w * tile_size, 3)

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

run_settings = run_setting(
    "H4sIAAAAAAAAA32UTXLbMAyF76J16pHdpNPJDXqGThYQCUkY8y8gWMfp9O6FnIX1Y2rhjf35AQ8PxO+/zS9Bf2xemxLMSCmhbZ5u352a1x5cxn9Pd6aDjC5GsRgyyfVOtofnOTcxvjih5Aj5jh0P7VpOGNJG7tguwQmiYBj1D/OiCwh8RxjE0TDKDFrokEdHnma//1ipZAEWCkMuaWo+V5Q+0gAUqs48CnTRUfYMglVsRHBaa5fpGYwUxrSqd3pZjNIh2l0dCj0aoRhywnnINcyMEMxOW9QxOQcTulvXx2hDZK9OPx/Q7WHpI4aSNaIO2EeuZq0peQrAOGA9BBABc7bgYdhpjwIN4FHd2jzCeUaeVjV1xMlcjcP9CWIwxXc8Tc9AqmJZOJ7n+yVclo+NNfGv7vuPOtZHNnjrrc64eJliwD/6PnYqOnovZFPJoy5lHbOUexp0Jb3K1bEQb10xqlP62ryd06J7p0kIOsii6Ya9M6TnwCJvFnR7NJRSSQ8+lnmn3x+B+sJi3+tBunPf1pKTmNVUr7sb76I5J9IPo6GsvuskXFH33FJPj/ysDen16lAuiAH1SI3vBRYL1B5+LnD0CbVRDWpr7GUpHfW0roa0epgWuzJcIrtNMG//AcSjL3hFBgAA"
)


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
