import pickle
from cparser.splitter import get_layer, collapse_biome_depth, collapse_kv
from cparser.structure_shorthand import structure_shorthand

BUILD_LAYER = 1
with open(r"terrgen.pkg", "rb") as f:
    src = pickle.load(f)

terr = src["WorldGenerateTerrain"]
genores = src["GenerateOres"]
structs = src["WorldGenerateStructures"]


print(
    collapse_biome_depth(genores, BUILD_LAYER),
    collapse_biome_depth(structs, BUILD_LAYER),
    get_layer(terr, BUILD_LAYER),
    sep="\n\n",
)
