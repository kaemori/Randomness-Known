import pickle
from pathlib import Path


def cache_output(fn, all_modules, filename=None):
    cache = Path.cwd() / f"_{fn.__name__}_cache.bin" if filename is None else filename

    if cache.is_file():
        try:
            with open(cache, "rb") as cache:
                return pickle.load(cache)
        except:
            pass
    with open(cache, "wb") as cache:
        obj = fn(all_modules)
        pickle.dump(obj, cache)
        return obj
