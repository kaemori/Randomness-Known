import regex

from cparser.ir_nodes import *
from cparser.transpiler import KNOWN_TYPES
from tools.collect_ternery import fix_ternary

INDENT = "    "


def expr_to_str(node):
    if node is None:
        return "None"
    if isinstance(node, Vector2Node):
        constructor = "Vector2"
        if node.kind == "Vector2Int":
            return (
                f"{constructor}(int({expr_to_str(node.x)}), int({expr_to_str(node.y)}))"
            )
        return f"{constructor}({expr_to_str(node.x)}, {expr_to_str(node.y)})"
    if isinstance(node, Vector3Node):
        return f"Vector3({expr_to_str(node.x)}, {expr_to_str(node.y)}, {expr_to_str(node.z)})"
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


def _noise_setting(lines, indent, node):
    arg = expr_to_str(node.args[0])

    ENUM_PREFIXES = {
        "FastNoiseLite.NoiseType.": "NoiseType.NoiseType_",
        "FastNoiseLite.FractalType.": "FractalType.FractalType_",
        "FastNoiseLite.CellularDistanceFunction.": "CellularDistanceFunction.CellularDistanceFunction_",
        "FastNoiseLite.CellularReturnType.": "CellularReturnType.CellularReturnType_",
    }

    def resolve_arg(a):
        for old, new in ENUM_PREFIXES.items():
            if a.startswith(old):
                return a.replace(old, new)
        return a

    PROPERTY_MAP = {
        "SetNoiseType": "noise_type",
        "SetFractalType": "fractal_type",
        "SetFrequency": "frequency",
        "SetFractalOctaves": "fractal_octaves",
        "SetFractalLacunarity": "fractal_lacunarity",
        "SetCellularDistanceFunction": "cellular_distance_function",
        "SetCellularReturnType": "cellular_return_type",
        "SetCellularJitter": "cellular_jitter",
        "SetFractalGain": "fractal_gain",
        "SetFractalWeightedStrength": "fractal_weighted_strength",
    }

    if prop := PROPERTY_MAP.get(node.method):
        reso = resolve_arg(arg)
        needs_brackets = "?" in reso and ":" in reso
        if needs_brackets:
            emit(lines, indent, f"{node.noise_var}.{prop} = ({reso})")
        else:
            emit(lines, indent, f"{node.noise_var}.{prop} = {reso}")
    else:
        emit(lines, indent, f"# {node.noise_var}.{node.method}({arg})")


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
            emit(lines, indent, f"worldBlocks[{x}, {y}] = {v}")

        case IfChain():
            convert_ifchain(node, lines, indent)

        case ForLoop():
            convert_forloop(node, lines, indent)

        case YieldReturn():
            if node.value is not None:
                emit(lines, indent, f"{expr_to_str(node.value)}  # was yield statement")

        case YieldBreak():
            emit(lines, indent, "# yield break")

        case NoiseConstruct():
            emit(
                lines,
                indent,
                f"{node.name} = FastNoiseLite(seed={expr_to_str(node.seed)})",
            )
            for setting in node.settings:
                convert_stmt(setting, lines, indent)

        case NoiseSetting():
            _noise_setting(lines, indent, node)

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
        emit(lines, indent, f"{target} {op} {expr_to_str(node.value)}")
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
    if forloop.init is not None:
        convert_stmt(forloop.init, lines, indent)

    emit(lines, indent, f"while {expr_to_str(forloop.condition)}:")
    convert_block(forloop.body, lines, indent + 1)

    if forloop.update is not None:
        convert_stmt(forloop.update, lines, indent + 1)


def convert_function(func, danger_make_returns_sysexit=False):
    lines = []
    # emit(lines, 0, "for_fixer = lambda x: math.ceil(x) if isinstance(x, float) else x")
    convert_block(func.body, lines, 0)

    litintfloat = regex.compile(r"\b((?<!\.)\d+(?!\.))f\b")
    litfloat = regex.compile(r"(-?[0-9]+(?:\.[0-9]+)?)f")
    litintsuffix = regex.compile(r"\b(\d+)(?:[uU]|[lL]|[uU][lL]|[lL][uU])\b")

    file = "\n".join(lines)

    for type in KNOWN_TYPES:
        file = file.replace(f"({type})", "")
    file = file.replace("&&", "and")
    file = file.replace("||", "or")
    file = file.replace("default(Vector2)", "Vector2(0, 0)")
    file = file.replace("default(Vector3)", "Vector3(0, 0, 0)")
    file = file.replace("Vector2Int.", "Vector2.")
    file = file.replace("null", "None")
    file = file.replace("int.MaxValue", "0x7FFFFFFF")
    file = file.replace(".GetNoise", ".get_noise")
    file = regex.sub(litintsuffix, r"\1", file)
    file = regex.sub(litintfloat, r"\1.0", file)
    file = regex.sub(litfloat, r"\1", file)
    file = fix_ternary(file)
    file = regex.sub(litintfloat, r"\1.0", file)
    file = regex.sub(litfloat, r"\1", file)
    if danger_make_returns_sysexit:
        nullreturn = regex.compile(r"(?m)^([ \t]*)return[ \t]*$")
        file = regex.sub(nullreturn, r'\1__import__("sys").exit(0)', file)

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
    # FUNCTION = "GenerateOres"
    # FUNCTION = "WorldGenerateTerrain"
    FUNCTION = "WorldGenerateStructures"
    genterr_entry = EntryPoint("WorldGeneration", FUNCTION)
    genterr_entry_line = genterr_entry.resolve(MODULE_INDEX)
    genterr_function_body = get_function_body(
        genterr_entry.module, genterr_entry_line, ALL_MODULES
    )

    genterr_function_body = clean_up_function(genterr_function_body)
    ir = transpile(genterr_function_body, FUNCTION)
    python_file = convert_function(ir, danger_make_returns_sysexit=True)

    output = Path().cwd() / "temp_genstruct.py"
    with open(output, "w") as w:
        print(python_file, file=w)
    # print(black.format_file_in_place(output, fast=False, mode=black.FileMode()))
