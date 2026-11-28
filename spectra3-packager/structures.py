from pathlib import Path
from functools import lru_cache
import math
import json
import re

import numpy as np
import yaml

from tools.textureloader import (
    get_blockinfo,
    get_guid_to_blockid as texture_guid_lookup,
)
from cparser.csfunc import module_init

ENTITY_SCRIPT_GUID = "68f22f20a50414ce34b083bddd64c702"
LADDER_SCRIPT_GUID = "4cce6cd47aacb3cb445380999484caa5"

PROJECT_PATH = Path(__file__).parent / "casproject"
ASSETS_PATH = PROJECT_PATH / "Assets"
RESOURCES_PATH = ASSETS_PATH / "Resources"
PREFABS_PATH = RESOURCES_PATH

_PREFAB_HEADER = re.compile(r"^--- !u!(\d+) &(-?\d+)(?: stripped)?\s*$", re.MULTILINE)
_STRUCTURE_LOAD = re.compile(
    r"""Resources\.Load(?:<\s*GameObject\s*>)?\s*\("""
    r"""\s*(?:GameObject\s*,\s*)?(['"])(.*?)\1"""
)

BLOCKINFO = None
GUID_TO_BLOCKID_LOOKUP = None


def initialize():
    global BLOCKINFO, GUID_TO_BLOCKID_LOOKUP
    module_init(
        decom_path=ASSETS_PATH / "Scripts" / "Assembly-CSharp",
        cache_path=PROJECT_PATH.parent / ".module_init_cache.pkl",
    )
    BLOCKINFO = get_blockinfo()
    GUID_TO_BLOCKID_LOOKUP = texture_guid_lookup(RESOURCES_PATH, BLOCKINFO)


def get_structure_set(genstruct_fn):
    source = genstruct_fn if isinstance(genstruct_fn, str) else "\n".join(genstruct_fn)
    resources = {match[1] for match in _STRUCTURE_LOAD.findall(source)}
    return {
        resource
        for resource in set(resources)
        if _resource_has_tilemap(resource, PREFABS_PATH)
    }


def get_resource_set(genstruct_fn):
    source = genstruct_fn if isinstance(genstruct_fn, str) else "\n".join(genstruct_fn)
    return {match[1] for match in _STRUCTURE_LOAD.findall(source)}


def _read_prefab(filepath):
    raw = filepath.read_text(encoding="utf-8")
    headers = list(_PREFAB_HEADER.finditer(raw))
    if not headers:
        raise ValueError(f"No Unity YAML documents found in {filepath}")

    normalized = re.sub(
        r"(?m)^%YAML.*(?:\r?\n)?|^%TAG.*(?:\r?\n)?|^--- !u!\d+ &-?\d+(?: stripped)?\s*$",
        lambda match: "---" if match.group(0).startswith("---") else "",
        raw,
    )
    documents = list(yaml.load_all(normalized, Loader=yaml.BaseLoader))
    if len(documents) != len(headers):
        raise ValueError(
            f"Unity YAML document/header count mismatch in {filepath}: "
            f"{len(documents)} documents, {len(headers)} headers"
        )

    by_fileid = {}
    for header, data in zip(headers, documents):
        fileid = header.group(2)
        if fileid in by_fileid:
            raise ValueError(f"Duplicate Unity file ID {fileid} in {filepath}")
        if data is not None and not isinstance(data, dict):
            raise ValueError(
                f"Invalid Unity document for file ID {fileid} in {filepath}"
            )
        by_fileid[fileid] = (header.group(1), data or {})
    return by_fileid


@lru_cache(maxsize=512)
def _prefab_has_tilemap(filepath, modified_ns, size):
    by_fileid = _read_prefab(Path(filepath))
    tilemap_ids = {
        fileid
        for fileid, (_, document) in by_fileid.items()
        if isinstance(document.get("Tilemap"), dict)
    }
    if not tilemap_ids:
        return False

    for _, (_, document) in by_fileid.items():
        game_object = document.get("GameObject")
        if game_object is None:
            continue
        component_ids = {
            str(component.get("component", {}).get("fileID"))
            for component in game_object.get("m_Component", [])
        }
        if tilemap_ids & component_ids:
            return True
    return False


def _resource_has_tilemap(resource, prefabs_path):
    root = Path(prefabs_path).resolve()
    filepath = (root / f"{resource}.prefab").resolve()
    if not filepath.is_relative_to(root):
        raise ValueError(f"Resource path must stay under {root}: {resource!r}")
    if not filepath.is_file():
        return False
    stat = filepath.stat()
    return _prefab_has_tilemap(str(filepath), stat.st_mtime_ns, stat.st_size)


def _as_float_vector(values, keys, defaults=None):
    defaults = defaults or {}
    try:
        return {key: float(values.get(key, defaults.get(key, 0))) for key in keys}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid vector data: {values!r}") from exc


def _quat_to_z_degrees(rotation):
    try:
        x, y, z, w = (float(rotation[key]) for key in ("x", "y", "z", "w"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid quaternion data: {rotation!r}") from exc
    magnitude = math.sqrt(x * x + y * y + z * z + w * w)
    if magnitude == 0:
        raise ValueError("Cannot convert a zero-length quaternion")
    x, y, z, w = (component / magnitude for component in (x, y, z, w))
    return math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def _extract_tilemaps(by_fileid, guid_to_blockid, filepath):
    tilemaps = []
    bounds = []
    for fileid, (_, document) in by_fileid.items():
        raw = document.get("Tilemap")
        if raw is None:
            continue

        tiles = raw.get("m_Tiles", [])
        if not tiles:
            continue
        try:
            locations = [
                (int(tile["first"]["x"]), int(tile["first"]["y"])) for tile in tiles
            ]
            x_low = min(x for x, _ in locations)
            x_high = max(x for x, _ in locations)
            y_low = min(y for _, y in locations)
            y_high = max(y for _, y in locations)
            tile_assets = raw["m_TileAssetArray"]
            lookup = []
            for index, asset in enumerate(tile_assets):
                guid = asset["m_Data"].get("guid", "-1")
                if guid not in guid_to_blockid:
                    raise KeyError(f"unknown tile GUID {guid!r}")
                lookup.append(guid_to_blockid[guid])
            tilemap = np.full(
                (x_high - x_low + 1, y_high - y_low + 1), -1, dtype=np.int32
            )
            for tile, (x, y) in zip(tiles, locations):
                tile_index = int(tile["second"]["m_TileIndex"])
                if not 0 <= tile_index < len(lookup):
                    raise IndexError(f"tile asset index {tile_index} is out of range")
                tilemap[x - x_low, y - y_low] = lookup[tile_index]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError(
                f"Invalid Tilemap file ID {fileid} in {filepath}: {exc}"
            ) from exc

        tilemaps.append(tilemap)
        bounds.append((x_low, y_low))
    return tilemaps, bounds


def _extract_entities(by_fileid, tilemap_bounds, filepath):
    entities = []
    for _, (component_type, document) in by_fileid.items():
        game_object = document.get("GameObject")
        if component_type != "1" or game_object is None:
            continue

        component_ids = []
        for component in game_object.get("m_Component", []):
            reference = component.get("component", {})
            fileid = reference.get("fileID")
            if fileid is not None:
                component_ids.append(str(fileid))

        transform = None
        box_collider = None
        entity_script = None
        ladder_script = None
        for component_id in component_ids:
            component_data = by_fileid.get(component_id)
            if component_data is None:
                continue
            component_type, component_document = component_data
            if component_type == "4":
                transform = component_document.get("Transform")
            elif component_type == "61":
                box_collider = component_document.get("BoxCollider2D")
            elif component_type == "114":
                mono_behaviour = component_document.get("MonoBehaviour", {})
                guid = mono_behaviour.get("m_Script", {}).get("guid")
                if guid == ENTITY_SCRIPT_GUID:
                    entity_script = mono_behaviour
                elif guid == LADDER_SCRIPT_GUID:
                    ladder_script = mono_behaviour

        if entity_script is None:
            continue
        if transform is None:
            raise ValueError(
                f"Entity GameObject {game_object.get('m_Name')!r} has no Transform "
                f"in {filepath}"
            )

        position = _as_float_vector(transform.get("m_LocalPosition", {}), "xyz")
        if tilemap_bounds:
            position["x"] -= tilemap_bounds[0][0]
            position["y"] -= tilemap_bounds[0][1]
        scale = _as_float_vector(
            transform.get("m_LocalScale", {}), "xyz", {"x": 1, "y": 1, "z": 1}
        )
        try:
            rotation = _quat_to_z_degrees(transform["m_LocalRotation"])
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid rotation for entity {game_object.get('m_Name')!r} "
                f"in {filepath}"
            ) from exc

        entry = {
            "id": entity_script.get("id") or game_object.get("m_Name"),
            "name": game_object.get("m_Name"),
            "position": position,
            "scale": scale,
            "rotation_deg": rotation,
        }
        if ladder_script is not None and box_collider is not None:
            tiling = box_collider.get("m_SpriteTilingProperty")
            entry["length"] = float(tiling["newSize"]["y"]) if tiling else None
        else:
            entry["length"] = -1
        entities.append(entry)
    return entities


def get_single_prefab(
    name,
    prefabs_path=PREFABS_PATH,
    guid_to_blockid=None,
):
    prefabs_path = Path(prefabs_path).resolve()
    relative_name = Path(name)
    if relative_name.suffix != ".prefab":
        relative_name = relative_name.with_suffix(".prefab")
    filepath = (prefabs_path / relative_name).resolve()
    if not filepath.is_relative_to(prefabs_path):
        raise ValueError(f"Prefab path must stay under {prefabs_path}: {name!r}")
    if not filepath.is_file():
        raise FileNotFoundError(filepath)

    if guid_to_blockid is None and GUID_TO_BLOCKID_LOOKUP is None:
        initialize()
    by_fileid = _read_prefab(filepath)
    if guid_to_blockid is None:
        guid_to_blockid = GUID_TO_BLOCKID_LOOKUP
    tilemaps, tilemap_bounds = _extract_tilemaps(by_fileid, guid_to_blockid, filepath)
    entities = _extract_entities(by_fileid, tilemap_bounds, filepath)
    return tilemaps, entities, tilemap_bounds


def build_structure_package(resources, output_path):
    if GUID_TO_BLOCKID_LOOKUP is None:
        initialize()
    packaged = {
        "format": "spectra3-structures-v1",
        "structures": {},
    }
    for resource in sorted(set(resources)):
        try:
            tilemaps, entities, bounds = get_single_prefab(resource)
        except FileNotFoundError:
            tilemaps, entities, bounds = [], [], []
        anchor_x, anchor_y = bounds[0] if bounds else (0, 0)
        packaged["structures"][resource] = {
            "tilemaps": [
                {
                    "tiles": [
                        [
                            int(x + tilemap_bounds[0] - anchor_x),
                            int(y + tilemap_bounds[1] - anchor_y),
                            int(tilemap[x, y]),
                        ]
                        for x in range(tilemap.shape[0])
                        for y in range(tilemap.shape[1])
                        if int(tilemap[x, y]) >= 0
                    ],
                }
                for tilemap, tilemap_bounds in zip(tilemaps, bounds)
            ],
            "entities": [
                {
                    "assetpath": entity.get("id") or entity.get("name"),
                    "id": entity.get("id"),
                    "name": entity.get("name"),
                    "position": entity["position"],
                    "scale": entity["scale"],
                    "rotation_deg": entity["rotation_deg"],
                    "length": entity["length"],
                }
                for entity in entities
            ],
        }

    if not packaged["structures"]:
        raise ValueError("No structure resources were found to package")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(packaged, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    return packaged


if __name__ == "__main__":
    # found structures:
    # {'Structures/RestSpot', 'Structures/BlueHeartCont', 'Structures/MiniPod', 'Structures/MedicalBuilding', 'Structures/WoodCross', 'Structures/SteelBridge', 'Lifepod', 'Structures/BrickLoot', 'LifepodStart', 'Structures/LongCorridor', 'Special/TutorialStructure', 'Special/EndLab', 'Structures/CrystalSpawnPlatform', 'Structures/CratePod', 'Structures/ChipSite', 'BioContainer', 'Structures/WoodHorizontal', 'Structures/SteelThing'}
    # from cparser.csfunc import getmodule_as_py

    # print(
    #     set().union(
    #         *map(
    #             lambda i: print(f"checking {i[0]}...") or get_structure_set(i[1]),
    #             getmodule_as_py("WorldGeneration").items(),
    #         )
    #     )
    # )

    # print(
    #     set().union(
    #         *map(get_structure_set, getmodule_as_py("WorldGeneration").values())
    #     )
    # )

    initialize()
    tm, blockentities, bounds = get_single_prefab("Structures/MiniPod")
    print(tm, blockentities)
