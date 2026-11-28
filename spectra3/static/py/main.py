import pickle
import numpy as np
from js import HTMLButtonElement, document
from pyodide.ffi import create_proxy

from astools.splitter import get_layer, collapse_biome_depth, collapse_kv
from gpu_fnl import noise, PERLIN, CELLULAR, OPENSIMPLEX2S, FBM, RIDGED

src = None


def build_layergen(build_layer):
    global src
    with open("terrgen.pkg", "rb") as f:
        src = pickle.load(f)
    terr = src["WorldGenerateTerrain"]
    genores = src["GenerateOres"]
    structs = src["WorldGenerateStructures"]

    print(
        collapse_biome_depth(genores, build_layer),
        collapse_biome_depth(structs, build_layer),
        get_layer(terr, build_layer),
        sep="\n\n",
    )


async def handle_click(event):
    build_layergen(10)

    output = document.getElementById("output")
    result = await noise(128, 128, seed=42, type=PERLIN, fractal=FBM, octaves=4)
    frequency_map = np.full((128, 128), 0.06, dtype="f4")
    mapped_result = await noise(128, 128, seed=43, type=CELLULAR, freq=frequency_map)
    simplex_result = await noise(
        64, 64, seed=44, type=OPENSIMPLEX2S, fractal=RIDGED, octaves=3
    )
    output.innerText = (
        f"Loaded terrgen.pkg ({type(src).__name__})\n"
        f"GPU noise: {result.shape}, min={result.min():.3f}, max={result.max():.3f}\n"
        f"GPU frequency-map noise: {mapped_result.shape}, "
        f"min={mapped_result.min():.3f}, max={mapped_result.max():.3f}\n"
        f"GPU OpenSimplex2S/RIDGED: {simplex_result.shape}, "
        f"min={simplex_result.min():.3f}, max={simplex_result.max():.3f}"
    )


def setup():
    btn: HTMLButtonElement = document.getElementById("run-btn")
    btn.innerText = "Run"
    btn.disabled = False
    btn.addEventListener("click", create_proxy(handle_click))


setup()
