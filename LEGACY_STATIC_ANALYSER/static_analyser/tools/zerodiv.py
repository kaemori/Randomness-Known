# because UNITY FUCKING EDDEFINES DIV BY ZERO AS FUCKING INFINTINITYYYTYTYYT5YTYGYERKL WQREUBETOULB FS HBVL'R

import ast
import math
import copy


class CSharpDivTransform(ast.NodeTransformer):
    DIV_OPS = (ast.Div, ast.FloorDiv)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, self.DIV_OPS):
            return ast.Call(
                func=ast.Name(id="__csharp_div__", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if isinstance(node.op, self.DIV_OPS):
            new_target = copy.deepcopy(node.target)
            new_target.ctx = ast.Load()
            call = ast.Call(
                func=ast.Name(id="__csharp_div__", ctx=ast.Load()),
                args=[new_target, node.value],
                keywords=[],
            )
            return ast.Assign(targets=[node.target], value=call)
        return node


def csharp_div(a, b):
    if b == 0:
        if a > 0:
            return math.inf
        elif a < 0:
            return -math.inf
        else:
            return math.nan
    return a / b
