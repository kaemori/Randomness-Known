# json_to_world.py
import json
import numpy as np


def load_structure_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def structure_to_blocks(struct, pad=4, fill_id=0, null_tile_id=0):
    x_min, x_max = struct["xMin"], struct["xMax"]
    y_min, y_max = struct["yMin"], struct["yMax"]

    width = (x_max - x_min) + pad * 2
    height = (y_max - y_min) + pad * 2

    arr = np.full((width, height), fill_id, dtype=np.uint16)

    for cell in struct["cells"]:
        x = cell["x"] - x_min + pad
        y = cell["y"] - y_min + pad
        block_id = cell["blockId"]
        if block_id < 0:
            block_id = null_tile_id
        arr[x, y] = block_id

    return arr


def save_world_npy(arr, out_path):
    np.save(out_path, arr)
    print(f"wrote {out_path}, shape={arr.shape}, dtype={arr.dtype}")
    uniques = np.unique(arr)
    print(f"unique block ids: {uniques}")


if __name__ == "__main__":
    import sys

    in_path = "./structures/BioContainer_child0_1.json"

    struct = load_structure_json(in_path)
    world = structure_to_blocks(struct)

    from cparser.csfunc import module_init
    from spectra2_rend import show_world
    from tools import textureloader
    from tools.world_state import WorldState

    w, h = world.shape

    world_state = WorldState.create(
        biome_depth=8 - 1,
        width=w,
        height=h,
        chunk_width=16,
        chunk_height=16,
        world_blocks=world,
    )

    module_init()

    show_world(world_state, textureloader.get_blockinfo())
