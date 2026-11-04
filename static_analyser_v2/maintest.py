from cparser.csfunc import (
    module_init,
    getmodule_as_py,
)

module_init()

with open("temp_gen/temp.py", "w") as f:
    for part in getmodule_as_py("WorldGeneration").values():
        for ovr in part:
            print(ovr + "\n", file=f)
