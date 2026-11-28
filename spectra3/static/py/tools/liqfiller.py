import numpy as np
from scipy import ndimage
from math import ceil

_STRUCT = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


def _fill_net(air):
    """Label connected air regions and build a flat index of cells per region."""
    W, H = air.shape
    labels, num = ndimage.label(air, structure=_STRUCT)

    # size of each connected region, keyed by label (0 = non-air)
    sizes = np.bincount(labels.ravel(), minlength=num + 1)
    out = np.where(air, sizes[labels], 0).astype(np.uint32)

    # flatten using the same i = x*H + y convention as before
    flat_idx = np.arange(W * H, dtype=np.int32)
    air_flat = air.ravel()
    labels_flat = labels.ravel()[air_flat]
    indices_flat = flat_idx[air_flat]

    # group all air cells by label, contiguously
    sort_order = np.argsort(labels_flat, kind="stable")
    order = indices_flat[sort_order]
    labels_sorted = labels_flat[sort_order]

    # first position of each label's group within `order`
    unique_labels, first_pos = np.unique(labels_sorted, return_index=True)
    start_by_label = np.zeros(num + 1, dtype=np.int64)
    start_by_label[unique_labels] = first_pos

    start = np.where(air, start_by_label[labels], 0).astype(np.int32)

    return out, start, order


def ensure_fillnet(env):
    if env.fillnet is not None:
        return
    env.fillnet, env.fillstart, env.fillorder = _fill_net(env.worldBlocks == 0)


def cached_fill(env, x, y, fill, max_fill):
    if not isinstance(fill, (int, np.integer)) or not 43 <= fill <= 65535:
        raise ValueError("liquid tile IDs must be integer values from 43 to 65535")
    if not 0 <= x < env.width or not 0 <= y < env.height:
        return False
    ensure_fillnet(env)
    n = int(env.fillnet[x, y])
    if n == 0 or n > max_fill:
        return False
    H = env.height
    s = int(env.fillstart[x, y])
    idx = env.fillorder[s : s + n]
    xs = idx // H
    ys = idx % H
    keep = env.fluid[xs, ys] == 0
    env.fluid[xs[keep], ys[keep]] = fill
    return True


# liquid fns
def place_liquids(env, per_chunk, liquid_type, max_fill):
    if not isinstance(liquid_type, (int, np.integer)) or not 43 <= liquid_type <= 65535:
        raise ValueError("liquid tile IDs must be integer values from 43 to 65535")
    ensure_fillnet(env)
    half_w, half_h = env.width // 2, env.height // 2
    rand = env.Random
    amount = env.chunkWidth * env.chunkHeight * per_chunk

    for _ in range(ceil(amount)):
        x = int(rand.Range(-half_w, half_w)) + half_w
        y = int(rand.Range(-half_h, half_h - 32)) + half_h
        cached_fill(env, x, y, liquid_type, max_fill)


def start_fill(env, block_pos, fill, max_fill):
    return cached_fill(env, int(block_pos.x), int(block_pos.y), fill, max_fill)
