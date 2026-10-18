import regex

from cparser.ir_nodes import *
from cparser.transpiler import KNOWN_TYPES
from functools import reduce

INDENT = "    "


def expr_to_str(node):
    if node is None:
        return "None"
    raw = getattr(node, "raw", None)
    if raw is not None:
        return raw
    return repr(node)


def emit(lines, indent, text):
    lines.append(f"{INDENT * indent}{text}")


def convert_block(block, lines, indent):
    if not block.body:
        emit(lines, indent, "pass")
        return
    for stmt in block.body:
        convert_stmt(stmt, lines, indent)


def _filter_expr_stmt(lines, indent, node):
    if isinstance(node.expr, MethodCall):
        if node.expr.target in ("this.SetLoadingText"):
            return

    emit(lines, indent, expr_to_str(node.expr))


def convert_stmt(node, lines, indent):
    kind = type(node).__name__

    # print(node)
    match node:
        case ExprStmt():
            _filter_expr_stmt(lines, indent, node)

        case VarDecl():
            convert_vardecl(node, lines, indent)

        case WorldBlockAssign():
            x = expr_to_str(node.x)
            y = expr_to_str(node.y)
            v = expr_to_str(node.value)
            emit(lines, indent, f"world_blocks[{x}, {y}] = {v}")

        case IfChain():
            convert_ifchain(node, lines, indent)

        case ForLoop():
            convert_forloop(node, lines, indent)

        case YieldReturn():
            if node.value is not None:
                emit(lines, indent, f"yield {expr_to_str(node.value)}")

        case YieldBreak():
            emit(lines, indent, "return")

        case NoiseConstruct():
            emit(
                lines,
                indent,
                f"{node.name} = FastNoiseLite(seed={expr_to_str(node.seed)})",
            )
            for setting in node.settings:
                convert_stmt(setting, lines, indent)

        case NoiseSetting():
            args = ", ".join(expr_to_str(a) for a in node.args)
            emit(lines, indent, f"{node.noise_var}.{node.method}({args})")

        case NoiseConfigure():
            # print(node)
            convert_stmt(node.setting, lines, indent)

        case Block():
            convert_block(node, lines, indent)

        case _:
            emit(lines, indent, f"# <{kind}> {expr_to_str(node)}")


def convert_vardecl(node, lines, indent):
    target = node.name
    op = node.compound_op

    if op == "++":
        emit(lines, indent, f"{target} += 1")
    elif op == "--":
        emit(lines, indent, f"{target} -= 1")
    elif op:
        emit(lines, indent, f"{target} {op}= {expr_to_str(node.value)}")
    else:
        emit(lines, indent, f"{target} = {expr_to_str(node.value)}")


def convert_ifchain(ifchain, lines, indent):
    filtered_arms = [
        arm
        for arm in ifchain.arms
        if arm.condition is None or "this.biomeOverride" not in arm.condition.raw
    ]
    for i, arm in enumerate(filtered_arms):
        if arm.condition is None:
            emit(lines, indent, "else:")
        else:
            keyword = "if" if i == 0 else "elif"
            emit(lines, indent, f"{keyword} {expr_to_str(arm.condition)}:")
        convert_block(arm.body, lines, indent + 1)


def convert_forloop(forloop, lines, indent):
    loopvar, limit = forloop.condition.raw.split(" < ")
    emit(lines, indent, f"for {loopvar} in range({limit}):")
    convert_block(forloop.body, lines, indent + 1)


def convert_function(func):
    lines = []
    prefix = "async def" if func.is_coroutine else "def"
    emit(lines, 0, f"{prefix} {func.name}(self):")
    convert_block(func.body, lines, 1)

    trinary = regex.compile(
        r"(?P<ternary>\((?P<cond>(?:[^()?:]|(?P>paren))*+)\s*\?\s*(?P<then>(?:[^()?:]|(?P>paren))*+)\s*:\s*(?P<else>(?:[^()?:]|(?P>paren))*+)\))(?(DEFINE)(?P<paren>\((?:(?P>ternary)|[^()]|(?P>paren))*+\)))"
    )
    litfloat = regex.compile(r"([-0-9.]+)f")

    file = "\n".join(lines)

    for type in KNOWN_TYPES:
        file = file.replace(f"({type})", "")
    file = file.replace("&&", "and")
    file = file.replace("||", "or")
    file = file.replace("new Vector2Int", "")
    file = file.replace("null", "None")
    for _ in range(3):
        file = regex.sub(trinary, r"(\g<then>if \g<cond>else \g<else>)", file)
    file = regex.sub(litfloat, r"\1", file)

    return file


if __name__ == "__main__":
    from helpers.function_getter import (
        EntryPoint,
        load_modules,
        load_module_index,
        get_function_body,
        find_function_lines,
    )

    from worldgen_tools import clean_up_function, get_blockinfo
    from tools.index_cache import cache_output
    from cparser.transpiler import transpile
    from pathlib import Path
    import black

    DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
    ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
    MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)
    genterr_entry = EntryPoint("WorldGeneration", "WorldGenerateTerrain")
    genterr_entry_line = genterr_entry.resolve(MODULE_INDEX)
    genterr_function_body = get_function_body(
        genterr_entry.module, genterr_entry_line, ALL_MODULES
    )

    genterr_function_body = clean_up_function(genterr_function_body)
    ir = transpile(genterr_function_body)
    python_file = convert_function(ir)

    output = Path().cwd() / "rawr.py"
    with open(output, "w") as w:
        start = "this = FastNoiseLite = Random = Object = Resources = Quaternion = None\nworld_blocks = []\n\n"
        print(start + python_file, file=w)
    print(black.format_file_in_place(output, fast=False, mode=black.FileMode()))
