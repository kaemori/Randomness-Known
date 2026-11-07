from pathlib import Path

import moderngl, numpy as np

OPENSIMPLEX2, PERLIN, VALUE, CELLULAR = range(4)
NONE, FBM, RIDGED, PINGPONG = range(4)

RESOURCE_DIR = Path(__file__).parent
TABLES = (RESOURCE_DIR / "tables.txt").read_text()
SRC = (RESOURCE_DIR / "fnlstripped.glsl").read_text().replace("<TABLES>", TABLES)
ctx = moderngl.create_standalone_context(require=430)
prog = ctx.compute_shader(SRC)
U = {
    name: prog[name]
    for name in (
        "size",
        "seed",
        "ntype",
        "ftype",
        "octaves",
        "use_fmap",
        "freq",
        "lacunarity",
        "gain",
        "wstrength",
        "pingpong",
        "jitter",
        "bounding",
    )
}
_uniform_values = {}
_out_bufs = {}
_fmap_bufs = {}
_dummy = ctx.buffer(reserve=4)


def _buffer_for(cache, size):
    buffer = cache.get(size)
    if buffer is None:
        buffer = cache[size] = ctx.buffer(reserve=size)
    return buffer


def _set_uniform(name, value):
    if _uniform_values.get(name) != value:
        U[name].value = value
        _uniform_values[name] = value


def noise(
    w,
    h,
    seed,
    type=OPENSIMPLEX2,
    freq=0.01,
    fractal=NONE,
    octaves=3,
    lacunarity=2.0,
    gain=0.5,
    weighted=0.0,
    pingpong=2.0,
    jitter=1.0,
) -> np.ndarray[tuple[int, int]]:
    """freq may be scalar or another [w, h] ndarray"""
    fmap = None if np.isscalar(freq) else np.ascontiguousarray(freq, dtype="f4")
    g = abs(gain)
    total = (
        1.0
        if octaves <= 1
        else (float(octaves) if g == 1.0 else (1.0 - g**octaves) / (1.0 - g))
    )

    out = _buffer_for(_out_bufs, w * h * 4)
    if fmap is None:
        fb = _dummy
    else:
        fb = _buffer_for(_fmap_bufs, fmap.nbytes)
        fb.write(fmap)
    out.bind_to_storage_buffer(0)
    fb.bind_to_storage_buffer(1)

    for k, v in (
        ("size", (w, h)),
        ("seed", seed),
        ("ntype", type),
        ("ftype", fractal),
        ("octaves", octaves),
        ("use_fmap", fmap is not None),
        ("freq", 0.0 if fmap is not None else float(freq)),
        ("lacunarity", lacunarity),
        ("gain", gain),
        ("wstrength", weighted),
        ("pingpong", pingpong),
        ("jitter", jitter),
        ("bounding", 1.0 / total),
    ):
        _set_uniform(k, v)

    prog.run((h + 15) // 16, (w + 15) // 16)
    res = np.empty((w, h), dtype="f4")
    out.read_into(res)
    return res
