from pathlib import Path
from dataclasses import dataclass
from types import SimpleNamespace
import math
import numpy as np
import regex
import yaml

from worldgen_tools import (
    clean_up_function,
    get_blockinfo,
    get_guid_to_blockid,
    get_id_image_mapping,
)
from worldviewer import show_world
from cparser.transpiler import transpile
from cparser.ir_nodes import *
from tools.index_cache import cache_output
from tools.unity_random import UnityRandom
from tools.vectors import Vector2, Vector3
from tools.runsettings_parser import run_setting
from helpers.function_getter import (
    EntryPoint,
    load_modules,
    load_module_index,
    get_function_body,
    find_function_lines,
)

ENTITY_SCRIPT_GUID = "68f22f20a50414ce34b083bddd64c702"
LADDER_SCRIPT_GUID = "4cce6cd47aacb3cb445380999484caa5"
RESOURCES_PATH = (
    Path(__file__).parent
    / "CasU-Decompiled"
    / "ExportedProject"
    / "Assets"
    / "Resources"
)
PREFABS_PATH = (
    Path().cwd() / "CasU-Decompiled" / "ExportedProject" / "Assets" / "Resources"
)
DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
BLOCKINFO = get_blockinfo(ALL_MODULES, MODULE_INDEX)
GUID_TO_BLOCKID_LOOKUP = get_guid_to_blockid(RESOURCES_PATH, BLOCKINFO)
WORLDGEN_MODULE = "WorldGeneration"
genstruct_entry = EntryPoint(WORLDGEN_MODULE, "WorldGenerateStructures")
genstruct_entry_line = genstruct_entry.resolve(MODULE_INDEX)

genstruct_function_body = get_function_body(
    genstruct_entry.module, genstruct_entry_line, ALL_MODULES
)


def _quat_to_z_degrees(rotation):
    z, w = float(rotation["z"]), float(rotation["w"])
    return math.degrees(2 * math.atan2(z, w))


def get_structure_set(genstruct_fn):
    structs = regex.compile(r'Resources\.Load<GameObject>\("(.*?)"\)')
    return set(structs.findall("".join(genstruct_fn)))


def _get_single_prefab(name):
    filepath = PREFABS_PATH / (name + ".prefab")
    if not filepath.exists():
        raise FileNotFoundError

    with open(filepath) as prefab:
        raw = prefab.read()
        content = "\n".join(
            "---" if regex.match(r"^--- !u!", line) else line
            for line in raw.splitlines()
            if not line.startswith("%TAG") and not line.startswith("%YAML")
        )
    datas = list(yaml.load_all(content, Loader=yaml.BaseLoader))
    headers = regex.findall(r"^--- !u!(\d+) &(-?\d+)", raw, flags=regex.M)
    by_fileid = {
        fileid: (utype, data) for (utype, fileid), data in zip(headers, datas) if data
    }

    # dbg
    import json, shutil

    dbg_place = Path().cwd() / "nya"
    if dbg_place.exists():
        shutil.rmtree(dbg_place)
    dbg_place.mkdir()
    (dbg_place / "all").mkdir()
    (dbg_place / "gameobjs").mkdir()
    for dbgi, dbg_data in enumerate(datas):
        if "Tilemap" in dbg_data.keys():
            # print(f"preview{dbgi}.temp")
            with open(dbg_place / f"preview{dbgi}.temp", "w") as dbg_output:
                json.dump(dbg_data, dbg_output, indent=4)
        if "GameObject" in dbg_data.keys():
            # print(f"preview{dbgi}.temp")
            with open(
                dbg_place / "gameobjs" / f"preview{dbgi}.temp", "w"
            ) as dbg_output:
                json.dump(dbg_data, dbg_output, indent=4)
        with open(dbg_place / "all" / f"preview{dbgi}.temp", "w") as allofem:
            json.dump(dbg_data, allofem, indent=4)

    # tiles
    tilemaps_raws = []
    for data in datas:
        if "Tilemap" in data.keys():
            tilemaps_raws.append(data)

    tilemap = []
    tilemap_bounds = []
    for raw in tilemaps_raws:
        try:
            raw = raw["Tilemap"]
            x_low, x_high = None, None
            y_low, y_high = None, None
            tiles = raw["m_Tiles"]
            for tile in tiles:
                loc = tile["first"]
                x, y = int(loc["x"]), int(loc["y"])
                x_low = x if x_low is None else min(x_low, x)
                x_high = x if x_high is None else max(x_high, x)
                y_low = y if y_low is None else min(y_low, y)
                y_high = y if y_high is None else max(y_high, y)

            lookup_guid = raw["m_TileAssetArray"]
            lookup = [
                GUID_TO_BLOCKID_LOOKUP[item["m_Data"].get("guid", "-1")]
                for item in lookup_guid
            ]

            tiles_arr = np.full(
                (x_high - x_low + 1, y_high - y_low + 1), -1, dtype=np.int32
            )
            for tile in raw["m_Tiles"]:
                loc = tile["first"]
                x, y = int(loc["x"]), int(loc["y"])
                tiles_arr[x - x_low, y - y_low] = lookup[
                    int(tile["second"]["m_TileIndex"])
                ]

            tilemap.append(tiles_arr)
            tilemap_bounds.append((x_low, y_low))
        except:
            continue

    # blockentities
    entities = []
    for _, (utype, data) in by_fileid.items():
        if utype != "1" or "GameObject" not in data:
            continue
        game_object = data["GameObject"]
        component_ids = [
            component["component"]["fileID"]
            for component in game_object.get("m_Component", [])
        ]

        transform = None
        box_collider = None
        entity_script = None
        ladder_script = None

        for component_id in component_ids:
            if component_id not in by_fileid:
                continue
            component_type, component_data = by_fileid[component_id]
            if component_type == "4":
                transform = component_data["Transform"]
            elif component_type == "61":
                box_collider = component_data["BoxCollider2D"]
            elif component_type == "114":
                mono_behaviour = component_data["MonoBehaviour"]
                guid = mono_behaviour["m_Script"]["guid"]
                if guid == ENTITY_SCRIPT_GUID:
                    entity_script = mono_behaviour
                elif guid == LADDER_SCRIPT_GUID:
                    ladder_script = mono_behaviour

        if entity_script is None or transform is None:
            continue

        position = {k: float(v) for k, v in transform["m_LocalPosition"].items()}
        if tilemap_bounds:
            ref_x_low, ref_y_low = tilemap_bounds[0]
            position["x"] -= ref_x_low
            position["y"] -= ref_y_low

        local_scale = transform.get("m_LocalScale", {"x": 1, "y": 1, "z": 1})

        entry = {
            "id": entity_script.get("id") or game_object.get("m_Name"),
            "name": game_object.get("m_Name"),
            "position": {key: float(position[key]) for key in ("x", "y", "z")},
            "scale": {key: float(local_scale[key]) for key in ("x", "y", "z")},
            "rotation_deg": _quat_to_z_degrees(transform["m_LocalRotation"]),
        }

        if ladder_script is not None and box_collider is not None:
            tiling = box_collider.get("m_SpriteTilingProperty")
            entry["length"] = float(tiling["newSize"]["y"]) if tiling else None
        else:
            entry["length"] = -1  # noop for convenience sake

        entities.append(entry)

    return tilemap, entities, tilemap_bounds


def _render_tilemap(tm, entities):
    to_show = tm
    viewer_data = SimpleNamespace(
        worldBlocks=to_show,
        fluid=np.zeros_like(to_show, dtype=np.uint8),
    )
    show_world(viewer_data, BLOCKINFO, entities=entities)


# a = set(
#     [
#         *[entity["id"] for entity in _get_single_prefab(prefab)[1]]
#         for prefab in get_structure_set(genstruct_function_body)
#     ]
# )
# print(a)
# for prefab in get_structure_set(genstruct_function_body):
#     print(prefab, [entity["id"] for entity in _get_single_prefab(prefab)[1]])

# tm, blockentities, _ = _get_single_prefab("structures/MedicalBuilding")
# tm, blockentities, _ = _get_single_prefab("structures/SteelBridge")
# tm, blockentities, _ = _get_single_prefab("structures/BrickLoot")
# tm, blockentities, _ = _get_single_prefab("structures/SteelThing")
# tm, blockentities, _ = _get_single_prefab("structures/CrystalSpawnPlatform")
# tm, blockentities, _ = _get_single_prefab("Lifepod")
# tm, blockentities, _ = _get_single_prefab("BioContainer")
# tm, blockentities, _ = _get_single_prefab("Structures/LongCorridor")

# print(blockentities)
# _render_tilemap(tm[0], blockentities)
# _get_single_prefab("BioContainer")
