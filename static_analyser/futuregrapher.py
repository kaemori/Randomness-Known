from pathlib import Path

from helpers.csharp_syntax import find_calls_in_lines, is_line_function
from helpers.function_getter import (
    EntryPoint,
    get_function_body,
    load_modules,
    load_module_index,
)
from check_overloads import write_overload_registry, read_overload_registry

from helpers.logging_helper import logger

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
OVERLOAD_PATH = Path(__file__).parent / "overload_reg.json"
ALL_MODULES = load_modules(DECOMPILED_PATH)
MODULE_INDEX = load_module_index(ALL_MODULES)
OVERLOADS = read_overload_registry(OVERLOAD_PATH)


# start creating weight graph
entry = EntryPoint("WorldGeneration", "GenerateWorld")
entry_line = entry.resolve(MODULE_INDEX)


def markov_chain(module_name, line_number):
    logger.debug(f"entering {module_name}.{line_number}")
    function_body = get_function_body(module_name, line_number, ALL_MODULES)
    calls = find_calls_in_lines(function_body)
    logger.debug(f"calls in {module_name}.{line_number}: {calls}")

    for module, called_function in calls:
        # naively ignore chained calls like "foo.bar.baz()"
        if module == "this":
            module = module_name

        if module not in ALL_MODULES:
            logger.warning(f"Module {module} not found")
            continue

        if called_function not in MODULE_INDEX[module]:
            logger.warning(f"Function {called_function} not found in module {module}")
            continue

        called_line = MODULE_INDEX[module][called_function]
        markov_chain(module, called_line)


markov_chain(entry.module, entry_line)
