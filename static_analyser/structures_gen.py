from dataclasses import dataclass
import numpy as np

from tools.context import WorldgenContext
from tools.generation_settings import GenerationSettings, RunSettings
from raycast_tools import Raycaster
from worldgen_tools import get_guid_to_blockid, get_id_image_mapping
from worldviewer import show_world
from cparser.ir_nodes import *
from tools.unity_random import UnityRandom
from tools.vectors import Vector2, Vector3
from tools.runsettings_parser import run_setting


@dataclass
class Physics2D:
    # just to bind it to the c# fn of the same name, Physics2D.Raycast
    raycaster: Raycaster

    def Raycast(self, origin, direction, max_distance, _):
        # source uses some sort of mask?
        return self.raycaster.raycast(origin, direction, max_distance)


def GenerateDropCapsules(gensettings, amt, context: WorldgenContext):
    print("generating dropcaps")
    dropcap_py = context.transpiler.get_python_code("GenerateDropCapsules")
    dropcap_py = dropcap_py.replace("this.", "")
    dropcap_py = dropcap_py.replace(
        ".GetComponent<AudioSource>().pitch = Random.Range(0.9, 1.1)",
        "; Random._next()",
    )  # why does this even have a sound when spawned
    with open("dropcap.tmp", "w") as f:
        print(dropcap_py, file=f)


def GenerateCollapsedPods(gensettings, amt, context: WorldgenContext): ...


def world_generate_structures(
    gensettings: GenerationSettings, context: WorldgenContext
):
    print("generating structures,")

    python_file = context.transpiler.get_python_code(
        "WorldGenerateStructures", danger_make_returns_sysexit=True
    )
    python_file = python_file.replace("this.", "")

    raycaster = Raycaster(gensettings)
    run_settings_as_dict = gensettings.run_settings.settings
    totalLootRarity = run_settings_as_dict["baselootdensity"] * (
        run_settings_as_dict["lootmultiplier"] ** gensettings.biomeDepth
    )

    with open("temp_genstruct.py", "w") as f:
        f.writelines(python_file)

    env_globals = gensettings.to_global_dict
    env_globals["totalLootRarity"] = totalLootRarity
    env_globals["GenerateDropCapsules"] = lambda gensettings, amt: GenerateDropCapsules(
        gensettings, amt, context
    )
    env_globals["GenerateCollapsedPods"] = (
        lambda gensettings, amt: GenerateCollapsedPods(gensettings, amt, context)
    )
    env_globals["Physics2D"] = Physics2D(raycaster)

    GenerateDropCapsules(gensettings, 0.2, context)
