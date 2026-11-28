import numpy as np
from numba import njit
from math import ceil


@njit(cache=True)
def _find(parent, a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


@njit(cache=True)
def _union(parent, size, head, tail, nxt, a, b):
    ra = _find(parent, a)
    rb = _find(parent, b)
    if ra == rb:
        return
    new_head = head[ra]
    new_tail = tail[rb]
    nxt[tail[ra]] = head[rb]
    if size[ra] < size[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    size[ra] += size[rb]
    head[ra] = new_head
    tail[ra] = new_tail


# nts: y=0 is bottom
@njit(cache=True)
def _ground_y(air):
    W, H = air.shape
    ground = np.full((W, H), -1, dtype=np.int32)
    for x in range(W):
        last_solid = -1
        for y in range(H):
            if air[x, y]:
                ground[x, y] = last_solid
            else:
                last_solid = y
    return ground


@njit(cache=True)
def _fill_net(air):
    W, H = air.shape
    n = W * H
    parent = np.arange(n).astype(np.int32)
    size = np.ones(n, dtype=np.int32)
    head = np.arange(n).astype(np.int32)
    tail = np.arange(n).astype(np.int32)
    nxt = np.full(n, -1, dtype=np.int32)

    seg_head = np.full((W, H), -1, dtype=np.int32)
    out = np.zeros((W, H), dtype=np.uint32)

    for y in range(H):
        for x in range(W):
            if not air[x, y]:
                continue
            i = x * H + y
            if x > 0 and air[x - 1, y]:
                _union(parent, size, head, tail, nxt, i, i - H)
            if y > 0 and air[x, y - 1]:
                _union(parent, size, head, tail, nxt, i, i - 1)
        for x in range(W):
            if air[x, y]:
                r = _find(parent, x * H + y)
                out[x, y] = size[r]
                seg_head[x, y] = head[r]

    total = 0
    for x in range(W):
        for y in range(H):
            if air[x, y]:
                total += 1
    order = np.empty(total, dtype=np.int32)
    pos = np.empty(n, dtype=np.int32)
    k = 0
    for i in range(n):
        if air[i // H, i % H] and parent[i] == i:
            j = head[i]
            while j != -1:
                order[k] = j
                pos[j] = k
                k += 1
                j = nxt[j]

    start = np.zeros((W, H), dtype=np.int32)
    for x in range(W):
        for y in range(H):
            if air[x, y]:
                start[x, y] = pos[seg_head[x, y]]
    return out, start, order


def ensure_fillnet(env):
    if env.fillnet is not None:
        return
    env.fillnet, env.fillstart, env.fillorder = _fill_net(env.worldBlocks == 0)


def ensure_groundy(env):
    if getattr(env, "groundy", None) is not None:
        return
    env.groundy = _ground_y(env.worldBlocks == 0)


def first_solid_below(env, x, y):
    ensure_groundy(env)
    by = int(env.groundy[x, y])
    return (x, by) if by >= 0 else (-1, -1)


def cached_fill(env, x, y, fill, max_fill):
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
