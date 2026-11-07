from pathlib import Path
import tree_sitter_c_sharp as tscs
from tree_sitter import Language, Parser
from collections import defaultdict
import functools
import textwrap
import pickle
import time

import os
from importlib.metadata import version as _pkg_version

_CACHE_VERSION = 1
_PYTHON_CACHE_VERSION = 2
_hasinit = False


def reqinit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _hasinit:
            raise NotImplementedError("run module_init first dummy")
        return func(*args, **kwargs)

    return wrapper


def showtime(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} finished in {time.time() - start:.2f}")
        return result

    return wrapper


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _text(node):
    return node.text.decode("utf-8", errors="replace") if node else None


def _cache_key():
    try:
        grammar = _pkg_version("tree-sitter-c-sharp")
    except Exception:
        grammar = "unknown"
    return (_CACHE_VERSION, grammar)


def _extract_methods(modbytes, root):
    func_map = defaultdict(list)
    for n in _walk(root):
        if n.type == "method_declaration":
            name = _text(n.child_by_field_name("name"))
            start = modbytes.rfind(b"\n", 0, n.start_byte) + 1
            end = modbytes.find(b"\n", n.end_byte)
            end = len(modbytes) if end == -1 else end
            src = (
                modbytes[start:end].decode("utf-8", errors="replace").replace("\r", "")
            )
            func_map[name].append(textwrap.dedent(src).replace("\t", "    "))
    return dict(func_map)


@showtime
def module_init(decom_path=None, cache_path=None, use_cache=True, write_cache=None):
    global _lang, _parser, _modules, _module_index, _module_python
    global _module_python_body
    global _module_trees, _decompiled_path, _hasinit

    _lang = Language(tscs.language())
    _parser = Parser(_lang)

    _decompiled_path = (
        Path(decom_path)
        if decom_path is not None
        else Path().cwd() / "casproject" / "Assets" / "Scripts" / "Assembly-CSharp"
    )
    if not _decompiled_path.exists():
        raise NotADirectoryError("check yo path")
    _modules = {file.stem: Path(file) for file in _decompiled_path.glob("*.cs")}
    _module_trees = {}
    _module_index = {}
    _module_python = {}
    _module_python_body = {}
    _hasinit = True

    cache_path = Path(cache_path) if cache_path else Path(".module_init_cache.pkl")

    cached_files = {}
    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)
            if data.get("key") == _cache_key() and data.get("root") == str(
                _decompiled_path.resolve()
            ):
                cached_files = data["files"]
        except Exception as e:
            print(f"cache unreadable ({e!r}), rebuilding")

    new_files = {}
    reparsed = 0
    python_cached = 0
    python_transpiled = 0
    python_unavailable = 0
    from cparser.transpiler import transpile_module

    for module, modpath in _modules.items():
        st = modpath.stat()
        sig = (st.st_mtime_ns, st.st_size)
        entry = cached_files.get(module)
        if entry and entry["sig"] == sig:
            func_map = entry["funcs"]
            python_map = entry.get("python")
            python_body_map = entry.get("python_body")
            if entry.get("python_key") != _PYTHON_CACHE_VERSION:
                python_map = None
                python_body_map = None
        else:
            modbytes = modpath.read_bytes()
            root = _parser.parse(modbytes).root_node
            _module_trees[module] = (modbytes, root)
            func_map = _extract_methods(modbytes, root)
            python_map = None
            python_body_map = None
            reparsed += 1
        if python_map is None:
            python_map = transpile_module(
                module, skip_unsupported=True, as_function=True
            )
            python_body_map = transpile_module(
                module, skip_unsupported=True, as_function=False
            )
            python_transpiled += 1
            if sum(map(len, python_map.values())) != sum(map(len, func_map.values())):
                python_unavailable += 1
        else:
            python_cached += 1
        _module_index[module] = func_map
        _module_python[module] = python_map
        _module_python_body[module] = python_body_map
        new_files[module] = {
            "sig": sig,
            "funcs": func_map,
            "python_key": _PYTHON_CACHE_VERSION,
            "python": python_map,
            "python_body": python_body_map,
        }

    if (
        use_cache
        or write_cache
        and (reparsed or python_transpiled or set(cached_files) != set(new_files))
    ):
        tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
        with open(tmp, "wb") as f:
            pickle.dump(
                {
                    "key": _cache_key(),
                    "root": str(_decompiled_path.resolve()),
                    "files": new_files,
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        os.replace(tmp, cache_path)

    print(
        f"{len(_modules)} modules ({python_transpiled} newly transpiled, {python_cached} caches. {python_unavailable} partial), {reparsed} reparsed, {len(_modules) - reparsed} from cache"
    )


def _get_tree(module):
    if module not in _module_trees:
        modbytes = _modules[module].read_bytes()
        _module_trees[module] = (modbytes, _parser.parse(modbytes).root_node)
    return _module_trees[module]


@reqinit
def getfunc(module, function, overload_no=None):
    lines = _module_index[module].get(function)
    if not lines:
        raise KeyError("wtf are you querying for??")
    if overload_no is None and len(lines) != 1:
        raise KeyError("overloads found, explicitly define overload_no!")
    return lines[0 if overload_no is None else overload_no]


@reqinit
def getfunc_as_py(module, function, overload_no=None, as_func=False):
    python_map = _module_python if as_func else _module_python_body
    functions = python_map[module].get(function)
    if not functions:
        raise KeyError("wtf are you querying for??")
    if overload_no is None and len(functions) != 1:
        raise KeyError("overloads found, explicitly define overload_no!")
    return functions[0 if overload_no is None else overload_no]


@reqinit
def getmodule_as_py(module):
    if module not in _modules:
        raise KeyError(f"unknown module {module!r}")
    return _module_python[module]


@reqinit
def getfunc_as_tree(module, name, overload_no=None):
    _, root = _get_tree(module)
    funcs = [
        n
        for n in _walk(root)
        if n.type == "method_declaration"
        and _text(n.child_by_field_name("name")) == name
    ]
    if not funcs:
        raise KeyError("wtf are you querying for??")
    if overload_no is None and len(funcs) != 1:
        raise KeyError("overloads found, explicitly define overload_no!")
    return funcs[0 if overload_no is None else overload_no]


@reqinit
def getmodule_as_tree(module, with_source=False):
    if module not in _modules:
        raise KeyError(f"unknown module {module!r}")
    modbytes, root = _get_tree(module)
    return (modbytes, root) if with_source else root


@reqinit
def getmodule_methods_as_tree(module):
    root = getmodule_as_tree(module)
    return [n for n in _walk(root) if n.type == "method_declaration"]
