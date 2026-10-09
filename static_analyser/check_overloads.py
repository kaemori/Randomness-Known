import json
from pathlib import Path

from helpers.function_getter import (
    find_function_lines,
    get_function_body,
    load_modules,
    load_module_index,
)
from helpers.csharp_syntax import find_calls_in_lines

from helpers.logging_helper import logger

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = load_modules(DECOMPILED_PATH)
MODULE_INDEX = load_module_index(ALL_MODULES)


def get_nth_overload(module_name, func_name, n):
    if module_name not in ALL_MODULES:
        raise ValueError(f"Module {module_name} not found")

    function_lines = find_function_lines(module_name, func_name, MODULE_INDEX)
    if len(function_lines) < n + 1:
        raise ValueError(
            f"Function {func_name} in module {module_name} has only {len(function_lines)} overloads, requested {n + 1}"
        )

    line_number = function_lines[n]
    function_body = get_function_body(module_name, line_number, ALL_MODULES)
    return function_body


def get_random_weight(
    this_function, this_funcbody, this_module, using_overload=0, _visited=None
):
    if _visited is None:
        _visited = set()

    call_id = (this_module, this_function, using_overload)
    if call_id in _visited:
        logger.debug(
            f"cycle detected at {this_module}.{this_function} overload {using_overload}, bailing"
        )
        return 0
    _visited.add(call_id)

    weight = 0
    calls = find_calls_in_lines(this_funcbody)
    logger.debug(
        f"getting random weight for {this_funcbody[0].strip()} in {this_module}, overload {using_overload}"
    )
    logger.debug("".join(this_funcbody))
    logger.debug(calls)

    for module, called_function in calls:
        if called_function == "PickRandom":
            # known random function
            weight += 1
            continue

        if module == "Random" and called_function == "Range":
            weight += 1
        else:
            if module == "this" or module == this_module:
                if called_function == this_function:
                    # case 1: recursive call to second overload
                    next_overload = 1 - using_overload
                    recursed_body = get_nth_overload(
                        this_module, this_function, next_overload
                    )
                    weight += get_random_weight(
                        this_function,
                        recursed_body,
                        this_module,
                        next_overload,
                        _visited,
                    )
                    continue
                else:
                    module = this_module

            if module in ALL_MODULES:
                try:
                    recursed_body = get_nth_overload(module, called_function, 0)
                except ValueError:
                    logger.debug(f"skipping {module}.{called_function}, not found")
                    continue
                weight += get_random_weight(
                    called_function, recursed_body, module, 0, _visited
                )

    return weight


def get_overloads():
    return {
        module_name: {
            func_name: lines for func_name, lines in funcs.items() if len(lines) > 1
        }
        for module_name, funcs in MODULE_INDEX.items()
    }


def _format_add(dictionary, module_name, func_name, weight):
    if dictionary.get(module_name) is None:
        dictionary[module_name] = {func_name: weight}
    else:
        dictionary[module_name][func_name] = weight


def create_overload_registry():
    overloads = get_overloads()
    collapsable = {}

    # manually add in issues later
    for module_name, funcs in overloads.items():
        for func_name, line_nums in funcs.items():
            logger.info(f"processing overload {func_name} ({len(line_nums)} overloads)")
            if len(line_nums) != 2:
                logger.info(f"{len(line_nums)} overloads found, expected 2")
                continue

            weights = []
            for overload_no, line_num in enumerate(line_nums):
                body = get_function_body(module_name, line_num, ALL_MODULES)
                weight = get_random_weight(func_name, body, module_name, overload_no)
                logger.debug(f"{module_name}:{line_num} random weight: {weight}")
                weights.append(weight)

            if weights[0] != weights[1]:
                logger.info(
                    f"overload {func_name} in {module_name} has different random weights: {weights}"
                )
            else:
                _format_add(collapsable, module_name, func_name, weights[0])

    # hardcode lol
    _format_add(collapsable, "Body", "HoldingItem", 0)
    _format_add(collapsable, "CraftingCourse", "SceneEntity", 0)
    _format_add(collapsable, "CraftingQuality", "CraftingQuality", 0)
    _format_add(collapsable, "Locale", "GetPdaNote", 1)
    _format_add(collapsable, "Locale", "GetCharacter", 0)
    _format_add(collapsable, "TutorialHandler", "AddBlockQuery", 0)
    _format_add(collapsable, "Utils", "PickRandom", 1)

    return collapsable


def write_overload_registry(output_file):
    overload_registry = create_overload_registry()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(overload_registry, f, indent=4)


def read_overload_registry(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        overload_registry = json.load(f)
    return overload_registry
