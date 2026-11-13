from pathlib import Path
from functools import partial
import time

import numpy as np
from PIL import Image

from cparser.csfunc import module_init, getfunc_as_tree, getfunc_as_py
from cparser.transpiler import transpile_method
from tools.animationcurve import AnimationCurve
from tools.unity_random import splitmix64
from tools.unity_shim import Plaything
from tools.generation_environment import Environment
from tools.run_settings import RunSettings
from tools.world_state import WorldState
from tools import textureloader

# from staticfunc.liqfiller import place_liquids, first_solid_below, ensure_groundy
import gc

gc.disable()

iceGenCurve = AnimationCurve.from_tuples(
    [
        (0, 0.04369995, -0.05734595, -0.05734595),
        (0.2, 0.03223076, -0.02508016, -0.02508016),
        (0.5213115, 0.03974618, -0.003112201, -0.003112201),
        (1, 0.0437015, 0.05906005, 0.05906005),
    ]
)

iceMinGenCurve = AnimationCurve.from_tuples(
    [
        (0, 0.001006186, 0.04270955, 0.04270955),
        (0.04285895, 0.001102524, 0.07020532, 3.843779),
        (0.4812723, 0.1877913, -0.6817608, -0.6817608),
        (0.8474102, 0.005548154, -0.1337805, -0.1337805),
        (0.9992933, 0.002213031, -0.001644637, -0.001644637),
    ]
)


def load_ice_map(width, height):
    path = Path(__file__).parent / "casproject" / "Assets" / "Texture2D" / "icemap.png"
    with Image.open(path) as image:
        source = np.asarray(image.convert("RGB"), dtype=np.float64)[::-1] / 255.0

    source_height, source_width, _ = source.shape
    x = np.arange(width, dtype=np.float64) / width * (source_width - 1)
    y = np.arange(height, dtype=np.float64) / height * (source_height - 1)
    x0 = np.floor(x).astype(np.intp)
    y0 = np.floor(y).astype(np.intp)
    x1 = np.minimum(x0 + 1, source_width - 1)
    y1 = np.minimum(y0 + 1, source_height - 1)
    x_weight = (x - x0)[None, :, None]
    y_weight = (y - y0)[:, None, None]

    top_left = source[y0[:, None], x0[None, :]]
    top_right = source[y0[:, None], x1[None, :]]
    bottom_left = source[y1[:, None], x0[None, :]]
    bottom_right = source[y1[:, None], x1[None, :]]
    samples = (
        top_left * (1.0 - x_weight) * (1.0 - y_weight)
        + top_right * x_weight * (1.0 - y_weight)
        + bottom_left * (1.0 - x_weight) * y_weight
        + bottom_right * x_weight * y_weight
    )
    return samples.transpose(1, 0, 2)


DUMP_DIR = Path("temp_gen")
DUMP_DIR.mkdir(exist_ok=True)
_dumped_files = []


def load_csfunc(module, func, replacements={}, istfg=True, use_istfg=False):
    if use_istfg:
        path = DUMP_DIR / f"{module}_{func}.py"
        return path.read_text()

    transpiled = getfunc_as_py(module, func, as_func=True)
    for replacement_pair in replacements:
        transpiled = transpiled.replace(*replacement_pair)
    if istfg:
        path = DUMP_DIR / f"{module}_{func}.py"
        if not path in _dumped_files:
            path.write_text(transpiled)
            _dumped_files.append(path)
    return transpiled


unity_random_state = splitmix64("purr")
run_settings = RunSettings.from_preset_str(
    "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
)


world_state = WorldState.create(
    biome_depth=8 - 1,
    width=1024,
    height=1024,
    chunk_width=16,
    chunk_height=16,
    run_settings=run_settings,
    random_state=unity_random_state,
)
iceMap = load_ice_map(world_state.width, world_state.height)

module_init(use_cache=False, write_cache=True)
# module_init()
MODULE = "WorldGeneration"
# print(textureloader.get_blockinfo())
textureloader.copy_icon_images(textureloader.get_blockinfo())
textureloader.copy_entity_images()


def gen_terr(env):
    func = "WorldGenerateTerrain"
    gen_terrain = load_csfunc(
        MODULE,
        func,
        (
            (
                "UnityEngine.Object.Instantiate(Resources.Load('Special/marbleBackground'), BlockToWorldPos(Vector2Int(num16, num17)), Quaternion.Euler(0.0, 0.0, UnityEngine.Random.value * 360.0))",
                "xs_next(xs_state)",
            ),
            ("iceMap.GetPixelBilinear(i / width, num34 / height)", "iceMap[i, num34]"),
            ("pixelBilinear.r", "pixelBilinear[0]"),
            ("pixelBilinear.g", "pixelBilinear[1]"),
            ("pixelBilinear.b", "pixelBilinear[2]"),
            (
                "pixelBilinear == Color.green",
                "pixelBilinear[0] == 0.0 and pixelBilinear[1] == 1.0 and pixelBilinear[2] == 0.0",
            ),
        ),
    )
    # print(gen_terrain)
    ns = {}
    exec(
        gen_terrain,
        env.as_dict
        | {
            "iceGenCurve": iceGenCurve,
            "iceMinGenCurve": iceMinGenCurve,
            "iceMap": iceMap,
        },
        ns,
    )
    try:
        ns[func]()
        # print(env.Random._count)
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
    # ensure_groundy(env)

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
    ).replace("return", "exit()")
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
        exec(
            load_csfunc(MODULE, "GenerateOres"),
            env.as_dict,
        ).replace("return", "exit()")
    except SystemExit:
        pass


# env = Environment(world_state, pl_fn=place_liquids, wgs_fn=gen_structs, go_fn=gen_ores)
# env = Environment(world_state, pl_fn=place_liquids, go_fn=gen_ores)
env = Environment(world_state)


st = time.time()
# __import__("cProfile").run("exec(gen_terrain, env.as_dict)", "nya.prof")
gen_terr(env)
# print(time.time() - st, env.Random._count)

from spectra2 import show_world, WorldFile

show_world(world_state, textureloader.get_blockinfo())


# WorldFile(
#     world_state.world_blocks, world_state.fluid, textureloader.get_blockinfo()
# ).save()

# show_world(world_state, textureloader.get_blockinfo())
