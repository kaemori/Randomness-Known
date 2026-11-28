import ast
import copy
from pathlib import Path


class CollapseConstants(ast.NodeTransformer):
    def __init__(self, consts):
        self.consts = consts

    def visit_Name(self, node):
        if node.id in self.consts:
            return ast.copy_location(ast.Constant(self.consts[node.id]), node)
        return node

    def _fold(self, test):
        for node in ast.walk(test):
            if isinstance(
                node,
                (
                    ast.Name,
                    ast.Call,
                    ast.Attribute,
                    ast.Subscript,
                    ast.Lambda,
                    ast.NamedExpr,
                ),
            ):
                return None

        try:
            return eval(
                compile(ast.Expression(test), "<fold>", "eval"),
                {"__builtins__": {}},
            )
        except Exception:
            return None

    def visit_Compare(self, node):
        node = self.generic_visit(node)
        result = self._fold(node)

        if result is not None:
            return ast.copy_location(ast.Constant(result), node)

        return node

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)

        values = []
        for value in node.values:
            result = self._fold(value)

            if result is None:
                values.append(value)
                continue

            if isinstance(node.op, ast.And) and not result:
                return ast.copy_location(ast.Constant(False), node)

            if isinstance(node.op, ast.Or) and result:
                return ast.copy_location(ast.Constant(True), node)

        node.values = values

        if not node.values:
            return ast.copy_location(
                ast.Constant(isinstance(node.op, ast.And)),
                node,
            )

        if len(node.values) == 1:
            return node.values[0]

        return node

    def visit_If(self, node):
        node = self.generic_visit(node)
        result = self._fold(node.test)

        if result is None:
            return node

        return node.body if result else node.orelse

    def visit_IfExp(self, node):
        node = self.generic_visit(node)
        result = self._fold(node.test)

        if result is None:
            return node

        return node.body if result else node.orelse


def find_dispatch(tree, const_name):
    for top_node in tree.body:
        if not isinstance(top_node, ast.If):
            continue

        current = top_node

        while isinstance(current, ast.If):
            names = {n.id for n in ast.walk(current.test) if isinstance(n, ast.Name)}

            if const_name in names:
                return current

            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
            else:
                break


def specialize_dispatch(dispatch, consts):
    branch = copy.deepcopy(dispatch)
    branch = CollapseConstants(consts).visit(branch)

    if isinstance(branch, list):
        return branch

    return [branch]


def collapse_kv(pycode, const_val):
    tree = ast.parse(pycode)
    tree = CollapseConstants(const_val).visit(tree)
    tree = ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def collapse_biome_depth(pycode, n):
    tree = ast.parse(pycode)
    tree = CollapseConstants({"biomeDepth": n}).visit(tree)
    tree = ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def get_layer(pycode, layer):
    tree = ast.parse(pycode)
    dispatch = find_dispatch(tree, "biomeDepth")
    statements = specialize_dispatch(dispatch, {"biomeDepth": layer})
    module = ast.Module(body=statements, type_ignores=[])
    module = ast.fix_missing_locations(module)
    return ast.unparse(module)
