import ast
import copy


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _is_call_named(node, name):
    return isinstance(node, ast.Call) and _dotted_name(node.func) == name


def _const(node):
    return node.value if isinstance(node, ast.Constant) else None


def _unwrap_loader(node):
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "GetComponent"
    ):
        return None
    base = node.func.value
    child_index = None

    if (
        isinstance(base, ast.Call)
        and isinstance(base.func, ast.Attribute)
        and base.func.attr == "GetChild"
        and isinstance(base.func.value, ast.Attribute)
        and base.func.value.attr == "transform"
    ):  # because nothing is consistent
        if base.args:
            child_index = _const(base.args[0])
        base = base.func.value.value

    if not (
        isinstance(base, ast.Call)
        and _dotted_name(base.func) == "Resources.Load"
        and len(base.args) == 2
    ):
        return None

    return _const(base.args[1]), child_index


class GenLoopExtractor:
    def __init__(self, loop_var_name):
        self.loop_var_name = loop_var_name

    def extract(self, while_node):
        body = list(while_node.body)
        if not body:
            return None

        info = {
            "ground": False,
            "entity": False,
            "circles": [],
            "resource_path": None,
            "child_index": None,
            "block_chance": None,
            "gen_mode": None,
        }

        idx = 0

        # gen-pos
        stmt = body[idx]
        if not (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)
            and _dotted_name(stmt.value.func) == "Vector2"
        ):
            return None
        idx += 1

        # snap to ground?
        if idx < len(body) and isinstance(body[idx], ast.Assign):
            maybe_ray = body[idx]
            if (
                isinstance(maybe_ray.value, ast.Call)
                and _dotted_name(maybe_ray.value.func) == "Physics2D.Raycast"
            ):
                ray_name = maybe_ray.targets[0].id
                idx += 1
                if (
                    idx < len(body)
                    and isinstance(body[idx], ast.If)
                    and isinstance(body[idx].test, ast.Name)
                    and body[idx].test.id == ray_name
                ):
                    info["ground"] = True
                    idx += 1

        # pos = WorldToBlockPos(vector)
        if idx >= len(body):
            return None
        stmt = body[idx]
        if not (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.value, ast.Call)
            and _dotted_name(stmt.value.func) == "WorldToBlockPos"
        ):
            return None
        pos_name = stmt.targets[0].id
        idx += 1

        # gen blockcircle
        while (
            idx < len(body)
            and isinstance(body[idx], ast.Expr)
            and _is_call_named(body[idx].value, "GenerateBlockCircle")
        ):
            args = body[idx].value.args
            info["circles"].append(tuple(_const(a) for a in args[1:]))
            idx += 1

        # GenerateObjectAtPos(pos, <loader chain>, chance, genMode)
        if idx >= len(body):
            return None
        stmt = body[idx]
        if not (
            isinstance(stmt, ast.Expr)
            and _is_call_named(stmt.value, "GenerateObjectAtPos")
        ):
            return None
        gcall = stmt.value
        if len(gcall.args) != 4:
            return None
        pos_arg, loader_call, chance_arg, mode_arg = gcall.args
        if not (isinstance(pos_arg, ast.Name) and pos_arg.id == pos_name):
            return None
        loaded = _unwrap_loader(loader_call)
        if loaded is None:
            return None
        info["resource_path"], info["child_index"] = loaded
        info["block_chance"] = _const(chance_arg)
        info["gen_mode"] = _const(mode_arg)
        idx += 1

        # background
        if (
            idx < len(body)
            and isinstance(body[idx], ast.Expr)
            and _is_call_named(body[idx].value, "GenerateEntityAtPos")
        ):
            info["entity"] = True
            idx += 1

        # i++
        if idx >= len(body):
            return None
        stmt = body[idx]
        if not (
            isinstance(stmt, ast.AugAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == self.loop_var_name
            and isinstance(stmt.op, ast.Add)
        ):
            return None
        idx += 1

        if idx != len(body):
            return None

        return info


def _make_call(num_expr, info):
    keywords = [
        ast.keyword(arg="ground", value=ast.Constant(value=info["ground"])),
        ast.keyword(arg="entity", value=ast.Constant(value=info["entity"])),
    ]
    if info["child_index"] is not None:
        keywords.append(
            ast.keyword(
                arg="child_index", value=ast.Constant(value=info["child_index"])
            )
        )
    if info["circles"]:
        circles_node = ast.List(
            elts=[
                ast.Tuple(elts=[ast.Constant(value=v) for v in circle], ctx=ast.Load())
                for circle in info["circles"]
            ],
            ctx=ast.Load(),
        )
        keywords.append(ast.keyword(arg="circles", value=circles_node))

    call = ast.Call(
        func=ast.Name(id="try_generate_specific", ctx=ast.Load()),
        args=[
            copy.deepcopy(num_expr),
            ast.Constant(value=info["resource_path"]),
            ast.Constant(value=info["block_chance"]),
            ast.Constant(value=info["gen_mode"]),
        ],
        keywords=keywords,
    )
    return ast.Expr(value=call)


def collapse_body(stmts):
    out = []
    i = 0
    n = len(stmts)
    while i < n:
        stmt = stmts[i]

        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value == 0
            and i + 1 < n
            and isinstance(stmts[i + 1], ast.While)
        ):
            loop_var = stmt.targets[0].id
            while_stmt = stmts[i + 1]
            cond = while_stmt.test
            cond_ok = (
                isinstance(cond, ast.Compare)
                and isinstance(cond.left, ast.Name)
                and cond.left.id == loop_var
                and len(cond.ops) == 1
                and isinstance(cond.ops[0], ast.Lt)
            )
            if cond_ok:
                num_expr = cond.comparators[0]
                info = GenLoopExtractor(loop_var).extract(while_stmt)
                if info is not None:
                    out.append(_make_call(num_expr, info))
                    i += 2
                    continue

        out.append(stmt)
        i += 1
    return out


class Collapser(ast.NodeTransformer):
    def visit_Module(self, node):
        node.body = collapse_body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        node.body = collapse_body(node.body)
        self.generic_visit(node)
        return node


def structure_shorthand(src: str) -> str:
    tree = ast.parse(src)
    tree = Collapser().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)
