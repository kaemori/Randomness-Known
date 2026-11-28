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

BIOME_DEPTH = 4

# module_init(use_cache=False, write_cache=True)
module_init()
# print(getmodule_as_py("WorldGeneration").keys())
# for method_node in getmodule_methods_as_tree("WorldGeneration"):
#     name = method_node.child_by_field_name("name").text.decode("utf-8")
#     if name == "WorldPlaceEntities":
#         transpile_method(method_node, as_function=False)


# terr_raw = getfunc_as_py("WorldGeneration", "WorldGenerateTerrain")
# oregen_raw = getfunc_as_py("WorldGeneration", "GenerateOres")

# # oregen = dirty_exit(collapse_biome_depth(oregen_raw, BIOME_DEPTH))
# oregen = oregen_raw
# terr = clean_exits(get_layer(terr_raw, BIOME_DEPTH))

# terr = terr.replace("GenerateOres()", f"\n# OreGen start\n{oregen}\n# OreGen end\n")

# with open(r"wawa.py", "w") as f:
#     print(terr, file=f)

struct_raw = structure_shorthand(
    collapse_kv(
        getfunc_as_py("WorldGeneration", "WorldGenerateStructures").replace(
            "OverrideSceneType.None", "None"
        ),
        {"biomeOverride": None},
    )
)

struct = get_layer(struct_raw, 4)

with open(r"wawa.py", "w") as f:
    print(struct, file=f)

dropcap_raw = getfunc_as_py("WorldGeneration", "GenerateDropCapsules")
dropcap = structure_shorthand(dropcap_raw)
print(dropcap)


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
