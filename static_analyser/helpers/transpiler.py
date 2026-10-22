from functools import cache

import irtopython

from cparser.transpiler import transpile
from worldgen_tools import clean_up_function
from helpers.function_getter import EntryPoint, get_function_body


class FunctionTranspiler:
    def __init__(self, worldgen_module, all_modules, module_index):
        self.worldgen_module = worldgen_module
        self.all_modules = all_modules
        self.module_index = module_index

    def get_function_body(self, fn_name):
        entry = EntryPoint(self.worldgen_module, fn_name)
        line = entry.resolve(self.module_index)
        if line is None:
            raise LookupError(f"Could not find {self.worldgen_module}.{fn_name}")
        return get_function_body(entry.module, line, self.all_modules)

    @cache
    def get_python_code(
        self, fn_name, danger_make_returns_sysexit=False, thisless=False
    ):
        body = clean_up_function(self.get_function_body(fn_name))
        ir = transpile(body, fn_name)
        py = irtopython.convert_function(
            ir, danger_make_returns_sysexit=danger_make_returns_sysexit
        )
        if thisless:
            py = py.replace("this.", "")
        return py
