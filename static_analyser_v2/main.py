from cparser.csfunc import (
    module_init,
    getfunc_as_tree,
)
from cparser.transpiler import transpile_method
from tools.unity_random import UnityRandom
from tools.generation_settings import GenerationSettings, RunSettings
from tools import textureloader

unity_random = UnityRandom.splitmixed("purr")
run_settings = RunSettings.from_preset_str(
    "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
)


gensettings = GenerationSettings(
    biomeDepth=3 - 1,
    width=1024,
    height=1024,
    chunkWidth=16,
    chunkHeight=16,
    run_settings=run_settings,
    Random=unity_random,
)

module_init()
textureloader.copy_icon_images(textureloader.get_blockinfo())
textureloader.copy_entity_images()
file = transpile_method(
    getfunc_as_tree("WorldGeneration", "WorldGenerateTerrain")
).replace("int.MaxValue", "0x7FFFFFFF")


file = "\n".join(
    [
        (
            line
            if "Resources.Load('Special/marbleBackground')" not in line
            else f"{(len(line) - len(line.lstrip())) * ' '}UnityEngine.Random.value  # step value"
        )
        for line in file.splitlines()
    ]
)

# with open("genterr.py", "w") as f:
#     print(file, file=f)

exec(file, gensettings.to_global_dict)

from spectra2 import show_world

show_world(gensettings, textureloader.get_blockinfo())
