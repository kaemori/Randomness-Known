Run the app from this directory with `python app.py`, then open `http://127.0.0.1:5000` in a browser with WebGPU support.

The `gpu_fnl` module in `static/py/gpu_fnl.py` runs the WGSL compute shader through the browser's WebGPU API. Since GPU dispatch is asynchronous in the browser, call it with `await`:

```python
from gpu_fnl import PERLIN, FBM, noise

field = await noise(1024, 1024, seed=123, type=PERLIN, fractal=FBM, octaves=5)
```

`field` is a NumPy array with shape `(width, height)`. `freq` can be a scalar or a NumPy frequency map with the same shape. The module exports `OPENSIMPLEX2`, `PERLIN`, `VALUE`, `CELLULAR`, `OPENSIMPLEX2S`, `NONE`, `FBM`, `RIDGED`, and `PINGPONG`.
