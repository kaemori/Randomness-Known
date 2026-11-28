import numpy as np
from js import gpuFnl, Object
from pyodide.ffi import to_js
from types import SimpleNamespace

OPENSIMPLEX2, PERLIN, VALUE, CELLULAR, OPENSIMPLEX2S = range(5)
NONE, FBM, RIDGED, PINGPONG = range(4)


async def noise(
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
):
    """Generate a (w, h) NumPy array using the browser's WebGPU device."""
    frequency_map = (
        None
        if np.isscalar(freq)
        else np.ascontiguousarray(freq, dtype="f4").reshape(-1)
    )
    options = {
        "width": int(w),
        "height": int(h),
        "seed": int(seed),
        "type": int(type),
        "freq": float(freq) if frequency_map is None else 0.0,
        "fractal": int(fractal),
        "octaves": int(octaves),
        "lacunarity": float(lacunarity),
        "gain": float(gain),
        "weighted": float(weighted),
        "pingpong": float(pingpong),
        "jitter": float(jitter),
        "frequencyMap": frequency_map,
    }
    js_options = to_js(options, dict_converter=Object.fromEntries)
    result = await gpuFnl.noise(js_options)
    return np.asarray(result.to_py(), dtype="f4").reshape((w, h))


pyglslfnl = SimpleNamespace(
    noise=noise,
    OPENSIMPLEX2=OPENSIMPLEX2,
    PERLIN=PERLIN,
    VALUE=VALUE,
    CELLULAR=CELLULAR,
    OPENSIMPLEX2S=OPENSIMPLEX2S,
    NONE=NONE,
    FBM=FBM,
    RIDGED=RIDGED,
    PINGPONG=PINGPONG,
)
