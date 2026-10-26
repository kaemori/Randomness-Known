import hashlib
import json
import numpy as np
from unity_random import UnityRandom, splitmix64, MASK


# ---- GF(2) jump-ahead -------------------------------------------------
def pack(s):
    return s[0] | s[1] << 32 | s[2] << 64 | s[3] << 96


def unpack(v):
    return tuple((v >> (32 * i)) & MASK for i in range(4))


def step_int(v):
    return pack(UnityRandom.xorshift128(*unpack(v)))


def apply(cols, v):  # matrix (list of 128 column ints) * vector
    r, i = 0, 0
    while v:
        if v & 1:
            r ^= cols[i]
        v >>= 1
        i += 1
    return r


def matmul(A, B):
    return [apply(A, c) for c in B]


def matpow(M, n):
    R = [1 << i for i in range(128)]  # identity
    while n:
        if n & 1:
            R = matmul(M, R)
        M = matmul(M, M)
        n >>= 1
    return R


M = [step_int(1 << i) for i in range(128)]  # one-step matrix


# ---- parallel generation ----------------------------------------------
def generate_u32(seed_state, amount, lanes=4096):
    B = -(-amount // lanes)  # ceil
    J = matpow(M, B)

    v = pack(seed_state)
    starts = []
    for _ in range(lanes):
        starts.append(unpack(v))
        v = apply(J, v)
    s0, s1, s2, s3 = (np.array(c, dtype=np.uint32) for c in zip(*starts))

    out = np.empty((B, lanes), dtype=np.uint32)
    for i in range(B):  # B ~ 2.4k iterations, each over 4096 lanes
        t = s0 ^ (s0 << 11)
        t ^= t >> 8
        t ^= s3 ^ (s3 >> 19)
        out[i] = t
        s0, s1, s2, s3 = s1, s2, s3, t

    return out.T.reshape(-1)[:amount]  # lane k -> contiguous block k


# ---- same output as your script ---------------------------------------
from PIL import Image

AMOUNT = 1000**2
img = Image.new("RGB", (1000, 1000))

u = generate_u32(splitmix64("nyan"), AMOUNT)
vals = ((u & 0x7FFFFF).astype(np.float64) / 0x7FFFFF).astype(np.float32)
aslist = vals.tolist()

for i, val in enumerate(aslist):
    x = i // 1000
    y = i % 1000
    px = round(val * 256)
    img.putpixel((x, y), (px, px, px))

img.save("nyann.png")

# encoded_data = json.dumps(tuple(vals.tolist()), sort_keys=True).encode("utf-8")
# sha256_hash = hashlib.sha256(encoded_data).hexdigest()
# print(sha256_hash)
