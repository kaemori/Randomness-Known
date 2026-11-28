from cparser.csfunc import (
    getmodule_methods_as_tree,
    module_init,
    getmodule_as_py,
    getfunc_as_py,
    getfunc_as_tree,
)
from cparser.transpiler import transpile_module, transpile_method
from cparser.splitter import get_layer, collapse_biome_depth, collapse_kv
from cparser.exitcleaner import clean_exits, dirty_exit
from cparser.structure_shorthand import structure_shorthand

import pickle

# BIOME_DEPTH = 4
# BIOME_DEPTH = 1

# module_init(use_cache=False, write_cache=True)
module_init()


with open(r"terrgen.pkg", "wb") as f:
    packaged = {
        "WorldGenerateTerrain": getfunc_as_py(
            "WorldGeneration", "WorldGenerateTerrain"
        ),
        "GenerateOres": getfunc_as_py(
            "WorldGeneration", "GenerateOres", as_func=True
        ).replace("exit()", "return"),
        "WorldGenerateStructures": structure_shorthand(
            collapse_kv(
                getfunc_as_py(
                    "WorldGeneration", "WorldGenerateStructures", as_func=True
                ).replace("OverrideSceneType.None", "None"),
                {"biomeOverride": None},
            )
        ),
        "GenerateTree": getfunc_as_py("WorldGeneration", "GenerateTree", as_func=True),
        "GenerateBigMushroom": getfunc_as_py(
            "WorldGeneration", "GenerateBigMushroom", as_func=True
        ),
        "WorldGenerateWorldBorders": getfunc_as_py(
            "WorldGeneration", "WorldGenerateWorldBorders"
        ),
        "WorldPlaceChip": getfunc_as_py("WorldGeneration", "WorldPlaceChip"),
        "WorldPlacePlayer": getfunc_as_py("WorldGeneration", "WorldPlacePlayer"),
        "WorldPlaceEntities": getfunc_as_py("WorldGeneration", "WorldPlaceEntities"),
        "DistributeEntities": getfunc_as_py(
            "WorldGeneration", "DistributeEntities", as_func=True
        ),
    }
    packaged = {k: v.replace("UpdateWorld()", "") for k, v in packaged.items()}
    pickle.dump(packaged, f)
    # terr_raw = getfunc_as_py("WorldGeneration", "WorldGenerateTerrain")
    # oregen_raw = getfunc_as_py("WorldGeneration", "GenerateOres")

    # oregen = dirty_exit(collapse_biome_depth(oregen_raw, BIOME_DEPTH))
    # terr = clean_exits(get_layer(terr_raw, BIOME_DEPTH))

    # terr = terr.replace("GenerateOres()", f"\n# OreGen start\n{oregen}\n# OreGen end\n")
    # print(terr, file=f)


# struct_raw = collapse_kv(
#     getfunc_as_py("WorldGeneration", "WorldGenerateStructures").replace(
#         "OverrideSceneType.None", "None"
#     ),
#     {"biomeOverride": None},
# )
# struct = structure_shorthand(get_layer(struct_raw, 6))

# with open(r"wawa.py", "w") as f:
#     print(struct, file=f)

# woodtrees = getfunc_as_py("WorldGeneration", "GenerateTree", as_func=True)

# with open(r"wawa.py", "w") as f:
#     print(woodtrees, file=f)

# bigmushrooms = getfunc_as_py("WorldGeneration", "GenerateBigMushroom", as_func=True)

# with open(r"wawa.py", "w") as f:
#     print(bigmushrooms, file=f)


# borders = clean_exits(collapse_biome_depth(getfunc_as_py("WorldGeneration", "WorldPlaceChip"), 2))

# with open(r"wawa.py", "w") as f:
#     print(borders, file=f)

# placeplayer = collapse_kv(
#     getfunc_as_py("WorldGeneration", "WorldPlacePlayer").replace(
#         "OverrideSceneType.None", "None"
#     ),
#     {"biomeOverride": None},
# )
# placeplayer = collapse_biome_depth(placeplayer, 0)

# with open(r"wawa.py", "w") as f:
#     print(placeplayer, file=f)

# entities_raw = collapse_kv(
#     getfunc_as_py("WorldGeneration", "WorldPlaceEntities").replace(
#         "OverrideSceneType.None", "None"
#     ),
#     {"biomeOverride": None},
# )
# entities = get_layer(entities_raw, 2)

# with open(r"wawa.py", "w") as f:
#     print(entities, file=f)


# distentities = getfunc_as_py("WorldGeneration", "DistributeEntities", as_func=True)

# with open(r"wawa.py", "w") as f:
#     print(distentities, file=f)
