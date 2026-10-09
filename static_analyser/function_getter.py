from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from csharp_syntax import get_method_declarations

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"


def load_modules(decompiled_path: str | Path = DECOMPILED_PATH) -> Dict[str, Path]:
    """Return {module_name: path} for every .cs file in *decompiled_path*."""
    decompiled_path = Path(decompiled_path)
    return {file.stem: file for file in decompiled_path.glob("*.cs")}


ModuleIndex = Dict[str, Dict[str, List[int]]]


def load_module_index(modules: Dict[str, Path]) -> ModuleIndex:
    """
    Parse every module with tree-sitter and build a full index of
    {module -> {function_name -> [line, ...]}} (multiple lines = overloads).

    Call once at startup; pass the result to all helpers below.
    """
    index: ModuleIndex = {}
    for module_name, path in modules.items():
        decls = get_method_declarations(path)
        func_map: Dict[str, List[int]] = {}
        for decl in decls:
            func_map.setdefault(decl.name, []).append(decl.line)
        index[module_name] = func_map
    return index


@dataclass
class EntryPoint:
    module: str
    function: str

    def resolve(self, index: ModuleIndex) -> Optional[int]:
        """
        Return the first (or only) line number for this function.
        Returns None if not found.
        Use find_function_lines() directly when you need all overloads.
        """
        lines = index.get(self.module, {}).get(self.function)
        return lines[0] if lines else None

    def resolve_all(self, index: ModuleIndex) -> List[int]:
        """Return all overload line numbers, or [] if not found."""
        return index.get(self.module, {}).get(self.function, [])


def find_function_lines(
    module: str,
    function: str,
    index: ModuleIndex,
) -> List[int]:
    """Return all line numbers for *function* in *module* (one per overload)."""
    return index.get(module, {}).get(function, [])


def get_function_body(
    module: str,
    line_number: int,
    modules: Dict[str, Path],
) -> List[str]:
    """
    Return the lines comprising the function that starts at *line_number*
    in *module*.  Uses brace counting which is reliable for ILSpy/dnSpy output.

    Returns [] if the module or line number is invalid.
    """
    path = modules.get(module)
    if path is None:
        return []

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    if line_number < 0 or line_number >= len(lines):
        return []

    depth = 0
    entered = False
    body: List[str] = []

    for line in lines[line_number:]:
        if entered and depth == 0:
            break

        opens = line.count("{")
        closes = line.count("}")

        if opens:
            entered = True

        depth += opens - closes
        body.append(line)

    return body


def get_function_from_line(
    module: str,
    line_number: int,
    index: ModuleIndex,
    modules: Dict[str, Path],
) -> Optional[Tuple[str, int]]:
    """
    Return (func_name, decl_line) for whichever function in *module* contains
    *line_number*, or None if it falls outside any known function.
    """
    func_map = index.get(module, {})
    path = modules.get(module)
    if not func_map or path is None:
        return None

    candidates: List[Tuple[int, str]] = sorted(
        (line, name) for name, lines in func_map.items() for line in lines
    )

    result: Optional[Tuple[str, int]] = None
    for decl_line, func_name in candidates:
        if decl_line > line_number:
            break
        body = get_function_body(module, decl_line, modules)
        end_line = decl_line + len(body) - 1
        if decl_line <= line_number <= end_line:
            result = (func_name, decl_line)

    return result
