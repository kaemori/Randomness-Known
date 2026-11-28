import ast
import pickle
import shutil
import textwrap
from pathlib import Path

from cparser.csfunc import getfunc_as_py
from cparser.splitter import (
    collapse_biome_depth,
    find_dispatch,
    get_layer,
)
from cparser.structure_shorthand import structure_shorthand
from structures import build_structure_package, get_resource_set, initialize


ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT
SPECTRA3_DIR = ROOT.parent / "spectra3" / "static" / "py"
LAYERS = tuple(range(11))
def _validate_python(source, name):
    try:
        ast.parse(source, filename=name)
    except SyntaxError as exc:
        raise ValueError(f"Invalid generated Python for {name}: {exc}") from exc


def build_package():
    initialize()
    terrain_source = getfunc_as_py(
        "WorldGeneration", "WorldGenerateTerrain"
    ).replace("UpdateWorld()", "")
    raw_structure_source = getfunc_as_py(
        "WorldGeneration", "WorldGenerateStructures", as_func=True
    ).replace("OverrideSceneType.None", "None")
    structure_source = structure_shorthand(raw_structure_source)

    raw_sources = {
        "GenerateOres": getfunc_as_py(
            "WorldGeneration", "GenerateOres", as_func=True
        ),
        "WorldGenerateStructures": structure_source,
        "GenerateTree": getfunc_as_py(
            "WorldGeneration", "GenerateTree", as_func=True
        ),
        "GenerateBigMushroom": getfunc_as_py(
            "WorldGeneration", "GenerateBigMushroom", as_func=True
        ),
        "GenerateDropCapsules": getfunc_as_py(
            "WorldGeneration", "GenerateDropCapsules", as_func=True
        ),
        "GenerateCollapsedPods": getfunc_as_py(
            "WorldGeneration", "GenerateCollapsedPods", as_func=True
        ),
        "GenerateLifePods": getfunc_as_py(
            "WorldGeneration", "GenerateLifePods", as_func=True
        ),
    }
    structure_resources = get_resource_set(
        "\n".join(
            (terrain_source, raw_structure_source, *(
                source
                for name, source in raw_sources.items()
                if name != "WorldGenerateStructures"
            ))
        )
    )
    for function_name in (
        "WorldGenerateStructures",
        "GenerateDropCapsules",
        "GenerateCollapsedPods",
        "GenerateLifePods",
    ):
        raw_sources[function_name] = structure_shorthand(
            raw_sources[function_name]
        )
    function_layers = {
        name: {
            str(layer): collapse_biome_depth(
                source.replace("UpdateWorld()", "").replace("exit()", "return"),
                layer,
            )
            for layer in LAYERS
        }
        for name, source in raw_sources.items()
    }

    terrain_tree = ast.parse(terrain_source)
    if find_dispatch(terrain_tree, "biomeDepth") is None:
        terrain_layers = {str(layer): terrain_source for layer in LAYERS}
    else:
        terrain_layers = {
            str(layer): get_layer(terrain_source, layer) for layer in LAYERS
        }

    for layer, source in terrain_layers.items():
        _validate_python(
            "async def _run():\n" + textwrap.indent(source, "    "),
            f"WorldGenerateTerrain[{layer}]",
        )
    for function_name, layer_map in function_layers.items():
        for layer, source in layer_map.items():
            _validate_python(source, f"{function_name}[{layer}]")

    structure_package_path = OUTPUT_DIR / "structures.pkg"
    build_structure_package(structure_resources, structure_package_path)

    packaged = {
        "format": "spectra3-terrgen-v1",
        "layers": list(LAYERS),
        "WorldGenerateTerrain": terrain_layers,
        "Functions": function_layers,
    }
    terrain_package_path = OUTPUT_DIR / "terrgen.pkg"
    with terrain_package_path.open("wb") as package_file:
        pickle.dump(packaged, package_file, protocol=pickle.HIGHEST_PROTOCOL)

    SPECTRA3_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(terrain_package_path, SPECTRA3_DIR / terrain_package_path.name)
    shutil.copy2(structure_package_path, SPECTRA3_DIR / structure_package_path.name)
    return packaged


if __name__ == "__main__":
    build_package()
