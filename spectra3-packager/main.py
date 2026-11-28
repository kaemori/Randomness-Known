from cparser.csfunc import module_init, getmodule_as_py, getfunc_as_py

module_init(use_cache=False)
terr = getfunc_as_py("WorldGeneration", "WorldGenerateTerrain")
with open(r"wawa.py", "w") as f:
    print(terr, file=f)
