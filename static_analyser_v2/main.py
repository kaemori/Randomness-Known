from pathlib import Path
from functools import partial
import time

from cparser.csfunc import (
    module_init,
    getfunc_as_tree,
)
from cparser.transpiler import transpile_method
from tools.unity_random import UnityRandom
from tools.unity_shim import Plaything
from tools.generation_environment import Environment
from tools.run_settings import RunSettings
from tools.world_state import WorldState
from tools import textureloader

from staticfunc.liqfiller import place_liquids, first_solid_below, ensure_groundy

DUMP_DIR = Path("temp_gen")
DUMP_DIR.mkdir(exist_ok=True)
_dumped_files = []


def load_csfunc(module, func, replacements={}, danger_retasext=False, istfg=True):
    transpiled = transpile_method(
        getfunc_as_tree(module, func), danger_return_as_exit=danger_retasext
    )
    for replacement_pair in replacements:
        transpiled = transpiled.replace(*replacement_pair)
    if istfg:
        path = DUMP_DIR / f"{module}_{func}.py"
        if not path in _dumped_files:
            path.write_text(transpiled)
            _dumped_files.append(path)
    return transpiled


unity_random = UnityRandom.splitmixed("purr")
run_settings = RunSettings.from_preset_str(
    "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
)


world_state = WorldState.create(
    biome_depth=1 - 1,
    width=1024,
    height=1024,
    chunk_width=16,
    chunk_height=16,
    run_settings=run_settings,
    random=unity_random,
)

module_init()
MODULE = "WorldGeneration"
textureloader.copy_icon_images(textureloader.get_blockinfo())
textureloader.copy_entity_images()


def gen_terr(env):
    gen_terrain = load_csfunc(
        MODULE,
        "WorldGenerateTerrain",
        (
            ("int.MaxValue", "0x7FFFFFFF"),
            (
                "UnityEngine.Object.Instantiate(Resources.Load('Special/marbleBackground'), BlockToWorldPos(Vector2Int(num16, num17)), Quaternion.Euler(0.0, 0.0, UnityEngine.Random.value * 360.0))",
                "UnityEngine.Random.value",
            ),
        ),
        danger_retasext=True,
    )
    try:
        exec(gen_terrain, env.as_dict)
    except SystemExit:
        pass


def _raycast(groundy, vector, direction, maxdist, _):
    if direction.x == 0 and direction.y == -1:
        print(vector.x, vector.y)
        itm = groundy[vector.x + 512, vector.y + 512]
        if itm == -1:
            return None
        return (vector.x - 512, itm - 512)
    raise NotImplementedError


def gen_structs(env):
    # theres a return at "if biomeDepth != 7"??
    ensure_groundy(env)

    getsetting = env.WorldGeneration.GetRunSettingFloat
    raycast = partial(_raycast, env.groundy)
    gen_struct = load_csfunc(
        MODULE,
        "WorldGenerateStructures",
        (
            ("OverrideSceneType.None", "None"),
            ("Physics2D.Raycast", "Raycast"),
            (".point", ""),
        ),
        danger_retasext=True,
    )
    try:
        exec(
            gen_struct,
            env.as_dict
            | {
                "totalLootRarity": (
                    getsetting("baselootdensity")
                    * (getsetting("lootmultiplier") ** (env.biomeDepth + 1))
                ),
                "Raycast": raycast,
                "LayerMask": Plaything(),
            },
        )
    except SystemExit:
        pass


def gen_ores(env):
    try:
        exec(load_csfunc(MODULE, "GenerateOres", danger_retasext=True), env.as_dict)
    except SystemExit:
        pass


env = Environment(world_state, pl_fn=place_liquids, wgs_fn=gen_structs, go_fn=gen_ores)
# env = Environment(world_state, pl_fn=place_liquids, wgs_fn=gen_structs)


st = time.time()
# __import__("cProfile").run("exec(gen_terrain, env.as_dict)", "nya.prof")
gen_terr(env)
print(time.time() - st, env.Random._count)

from spectra2 import show_world, WorldFile

# WorldFile(
#     world_state.world_blocks, world_state.fluid, textureloader.get_blockinfo()
# ).save()

show_world(world_state, textureloader.get_blockinfo())
