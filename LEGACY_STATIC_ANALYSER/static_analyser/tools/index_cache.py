import pickle
from pathlib import Path


def cache_output(fn, all_modules, filename=None):
    cache_path = (
        Path.cwd() / f"_{fn.__name__}_cache.bin" if filename is None else filename
    )

    if cache_path.is_file():
        try:
            with open(cache_path, "rb") as cache_file:
                return pickle.load(cache_file)
        except:
            pass
    with open(cache_path, "wb") as cache_file:
        obj = fn(all_modules)
        pickle.dump(obj, cache_file)
        return obj
