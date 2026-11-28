After the two package assets have been generated, run the app from this directory with `python app.py`, then open `http://127.0.0.1:5000` in a browser with WebGPU support. Select any layer from 0 to 10 and click **Generate world**; the page reports generated solid tiles, liquid tiles, and entities without drawing a canvas.

The browser loads two read-only package assets:

- `static/py/terrgen.pkg` contains the transpiled terrain, ore, structure, tree, and mushroom generators specialized for all eleven layers.
- `static/py/structures.pkg` contains sparse prefab tilemaps and entity transforms extracted from the decompiled Unity project, serialized as versioned JSON.

To build or refresh these assets, place the decompiled CAS project's `Assets` tree in `spectra3-packager/casproject` and run `python packager.py` from `spectra3-packager`. The packager writes both packages there and copies them into spectra3's static directory. The CAS assets are intentionally not checked in; generated package assets are intended to be committed as read-only browser inputs. Generation requires a browser with WebGPU; terrain noise calls are awaited through the GPU FNL shim.

The `gpu_fnl` module in `static/py/gpu_fnl.py` runs the WGSL compute shader through the browser's WebGPU API. Since GPU dispatch is asynchronous in the browser, call it with `await`:

```python
from gpu_fnl import PERLIN, FBM, noise

field = await noise(1024, 1024, seed=123, type=PERLIN, fractal=FBM, octaves=5)
```

`field` is a NumPy array with shape `(width, height)`. `freq` can be a scalar or a NumPy frequency map with the same shape. The module exports `OPENSIMPLEX2`, `PERLIN`, `VALUE`, `CELLULAR`, `OPENSIMPLEX2S`, `NONE`, `FBM`, `RIDGED`, and `PINGPONG`.

The serialized world model has one integer `worldblocks` grid: `0` is air, `1`-`42` are solid tile IDs, and `43+` are liquid tile IDs. `worldentities` is a separate list of records with an `assetpath` and a transform containing a two-dimensional position, degree rotation, and `isFlipped` flag.
