from pathlib import Path
from dataclasses import dataclass, make_dataclass
import regex as re

from helpers.csharp_syntax import find_calls_in_lines, is_line_function
from helpers.function_getter import (
    EntryPoint,
    get_function_body,
    load_modules,
    load_module_index,
)
from cparser.transpiler import transpile

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = load_modules(DECOMPILED_PATH)
MODULE_INDEX = load_module_index(ALL_MODULES)


# grab block ref
def get_blockinfo(all_modules, module_index):
    entry = EntryPoint("WorldGeneration", "GetBlockInfo")
    entry_line = entry.resolve(module_index)

    blocks = {}
    pending_case = None
    lines_to_skip = 0

    function_body = get_function_body(entry.module, entry_line, all_modules)
    for line in function_body:
        line = line.strip()

        if lines_to_skip > 0:
            lines_to_skip -= 1
            continue

        if "case" in line:
            pending_case = int(line.split("case")[1].split(":")[0].strip())
            lines_to_skip = 2
        elif pending_case is not None:
            name = line.split('("')[1].split('")')[0]
            blocks[pending_case] = name
            pending_case = None

    # {0: 'air', 1: 'lightrock', 2: 'gravel', 3: 'scrappile', 4: 'trashpile', 5: 'concretetile', 6: 'steeltile', 7: 'glass', 8: 'rubber', 9: 'plastic', 10: 'heatresistantalloy', 11: 'wood', 12: 'sand', 13: 'sandstone', 14: 'infinirock', 15: 'clay', 16: 'soil', 17: 'granite', 18: 'marble',19: 'limestone', 20: 'bricks', 21: 'scaffolding', 22: 'toxirock', 23: 'grass', 24: 'log', 25: 'leaves', 26: 'snow', 27: 'ice', 28: 'thinice', 29: 'powdersnow', 30: 'heavyrock', 31: 'fungus', 32: 'mushroombody', 33: 'mushroomcap', 34: 'copper', 35: 'ilmenite'}
    return blocks


def _normalize_addone(func):
    addone = re.compile(r"^((?:\s{4})*)(\w*) = (\w*);\n\1\3 = \2 \+ 1;", re.MULTILINE)
    return (
        re.sub(addone, r"\1\3++;", "".join(func))
        .replace("int num2;\n", "")
        .splitlines(keepends=True)
    )


def clean_up_function(function):
    while_loop = re.compile(
        r"^((?:\s{4})*)(?:\S)*\s*(\S*)\s*=\s*0;\n"
        r"(?>^(?:\s{4})*while[^<]*\< .*?([^()]+)\)+$)\n"
        r"^(?:\s{4})*\{\n"
        r"((?:\n|.)*?)\n"
        r"^\1\s{4}\2\+\+;\n",
        re.MULTILINE,
    )

    function = [line.replace("\t", "    ")[4:] for line in function]
    function = _normalize_addone(function)
    function_body_str = "".join(function)
    last_function_body_str = None
    while last_function_body_str != function_body_str:
        last_function_body_str = function_body_str
        function_body_str = re.sub(
            while_loop,
            r"\1for (int \2 = 0; \2 < \3; \2++)\n\1{\n\4\n",
            function_body_str,
        )

    return function_body_str.splitlines(keepends=True)


if __name__ == "__main__":
    # with open("terr_ir.cs", "w") as ir:
    #     entry = EntryPoint("WorldGeneration", "WorldGenerateTerrain")
    #     entry_line = entry.resolve(MODULE_INDEX)

    #     function_body = get_function_body(entry.module, entry_line, ALL_MODULES)
    #     function_body = clean_up_function(function_body)
    #     ir.writelines(function_body)
    with open("gen_ores.cs", "w") as ir:
        entry = EntryPoint("WorldGeneration", "GenerateOres")
        entry_line = entry.resolve(MODULE_INDEX)

        function_body = get_function_body(entry.module, entry_line, ALL_MODULES)
        function_body = clean_up_function(function_body)
        ir.writelines(function_body)
