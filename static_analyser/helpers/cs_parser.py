from pathlib import Path
from typing import Dict

from tree_sitter import Language, Parser
import tree_sitter_c_sharp as tscsharp

CS_LANG = Language(tscsharp.language())
_parser = Parser(CS_LANG)

_cache: Dict[Path, tuple] = {}


def get_tree(path: Path):
    """Return a cached parse tree for *path*, reparsing only when the file changes."""
    path = Path(path)
    mtime = path.stat().st_mtime
    cached = _cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    source = path.read_bytes()
    tree = _parser.parse(source)
    _cache[path] = (mtime, tree)
    return tree


def find_nodes(node, type_name: str):
    """Recursively collect all nodes of a given type."""
    results = []
    if node.type == type_name:
        results.append(node)
    for child in node.children:
        results.extend(find_nodes(child, type_name))
    return results
