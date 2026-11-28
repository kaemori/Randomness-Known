from cparser.csfunc import module_init, getmodule_methods_as_tree, _text
from cparser.transpiler import transpile_method

module_init()

for node in getmodule_methods_as_tree("WorldGeneration"):
    name = _text(node.child_by_field_name("name"))
    try:
        transpile_method(node, as_function=True)
    except Exception as e:
        print(f"{name}: {type(e).__name__}: {e}")
