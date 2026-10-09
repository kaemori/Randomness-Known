from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from cs_parser import CS_LANG, _parser, find_nodes

logger = logging.getLogger(f"jarvis.{__name__}")


@dataclass
class MethodDecl:
    name: str
    line: int  # 0-indexed line of the declaration
    is_constructor: bool = False


def is_line_function(line: str) -> Tuple[bool, Optional[str]]:
    """
    Return (True, func_name) if *line* looks like a C# method/constructor
    declaration, otherwise (False, None).

    Parses the single line in isolation so callers don't need a full file.
    This is kept for backward-compat with code that scans line-by-line.
    For whole-file analysis prefer get_method_declarations().
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("//"):
        return False, None

    if "(" not in stripped:
        return False, None

    snippet = f"class _Probe_ {{\n{stripped}\n}}\n"
    tree = _parser.parse(snippet.encode())

    _CS_KEYWORDS = {
        "if",
        "else",
        "for",
        "while",
        "switch",
        "foreach",
        "using",
        "lock",
        "catch",
        "when",
        "return",
        "new",
        "do",
        "try",
        "finally",
        "yield",
    }

    for node_type in ("method_declaration", "constructor_declaration"):
        nodes = find_nodes(tree.root_node, node_type)
        if nodes:
            name_node = nodes[0].child_by_field_name("name")
            if name_node:
                name = name_node.text.decode()
                if name not in _CS_KEYWORDS:
                    return True, name

    return False, None


def get_method_declarations(path: Path) -> List[MethodDecl]:
    """
    Parse an entire .cs file and return every method/constructor declaration
    with its 0-indexed start line.  Much faster than calling is_line_function
    per line because the file is parsed once.
    """
    from cs_parser import get_tree

    tree = get_tree(path)
    results: List[MethodDecl] = []

    for node in find_nodes(tree.root_node, "method_declaration"):
        name_node = node.child_by_field_name("name")
        if name_node:
            results.append(
                MethodDecl(
                    name=name_node.text.decode(),
                    line=node.start_point[0],
                )
            )

    for node in find_nodes(tree.root_node, "constructor_declaration"):
        name_node = node.child_by_field_name("name")
        if name_node:
            results.append(
                MethodDecl(
                    name=name_node.text.decode(),
                    line=node.start_point[0],
                    is_constructor=True,
                )
            )

    results.sort(key=lambda d: d.line)
    return results


def _get_direct_caller(expr_node) -> Optional[str]:
    """
    Given the *expression* child of a member_access_expression, return the
    name of the direct object the method is dispatched on:

        this.Foo()          -> "this"
        base.Foo()          -> "base"
        Random.Range()      -> "Random"
        this.obj.SetActive  -> "obj"   (last named segment before the dot)
        foo.Bar().Baz()     -> None    (dynamic — Bar() result, not a name)

    Note: tree-sitter represents `this` and `base` as nodes whose .type IS
    the string "this" / "base", not "this_expression" / "base_expression".
    """
    t = expr_node.type

    if t in ("this", "base"):
        return t

    if t == "identifier":
        return expr_node.text.decode()

    if t == "member_access_expression":
        name = expr_node.child_by_field_name("name")
        if name:
            return name.text.decode()

    return None


def find_calls_in_lines(lines: List[str]) -> List[Tuple[str, str]]:
    """
    Return a list of (caller, method) pairs for every method call found in
    *lines*.  Calls where the caller cannot be statically determined (e.g.
    the result of another call) are omitted.

    'caller' is the direct object name:
        this.Foo()          -> ("this", "Foo")
        Random.Range(0,5)   -> ("Random", "Range")
        this.obj.SetActive  -> ("obj", "SetActive")
        foo.Bar().Baz()     -> omitted (dynamic)
        BareCall()          -> omitted (no explicit caller)
    """
    if not lines:
        return []

    source = "".join(lines).encode()
    tree = _parser.parse(source)

    calls: List[Tuple[str, str]] = []
    seen: set = set()

    for inv in find_nodes(tree.root_node, "invocation_expression"):
        func = inv.child_by_field_name("function")
        if func is None or func.type != "member_access_expression":
            continue

        expr = func.child_by_field_name("expression")
        name = func.child_by_field_name("name")
        if expr is None or name is None:
            continue

        caller = _get_direct_caller(expr)
        if caller is None:
            continue

        method = name.text.decode()
        entry = (caller, method)

        if entry not in seen:
            seen.add(entry)
            calls.append(entry)

    return calls
