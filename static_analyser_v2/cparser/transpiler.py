import ast
import re

BINOPS = {
    "+": ast.Add,
    "-": ast.Sub,
    "*": ast.Mult,
    "/": ast.Div,
    "%": ast.Mod,
    "<<": ast.LShift,
    ">>": ast.RShift,
    "&": ast.BitAnd,
    "|": ast.BitOr,
    "^": ast.BitXor,
}
CMPOPS = {
    "<": ast.Lt,
    ">": ast.Gt,
    "<=": ast.LtE,
    ">=": ast.GtE,
    "==": ast.Eq,
    "!=": ast.NotEq,
}
BOOLOPS = {"&&": ast.And, "||": ast.Or}


class Transpiler:
    def __init__(self):
        self.types = {}

    def t(self, n):
        return n.text.decode("utf-8")

    def fail(self, n):
        raise NotImplementedError(
            f"{n.type} line {n.start_point[0]+1}: {self.t(n)[:60]!r}"
        )

    def expr(self, n):
        h = getattr(self, "e_" + n.type, None)
        return h(n) if h else self.fail(n)

    def stmt(self, n):
        h = getattr(self, "s_" + n.type, None)
        return h(n) if h else self.fail(n)

    def block(self, n):
        body = []
        for c in n.named_children:
            body += self.stmt(c)
        return body or [ast.Pass()]

    def body(self, n):
        return self.block(n) if n.type == "block" else self.stmt(n) or [ast.Pass()]

    def e_identifier(self, n):
        return ast.Name(self.t(n), ast.Load())

    def e_boolean_literal(self, n):
        return ast.Constant(self.t(n) == "true")

    def e_null_literal(self, n):
        return ast.Constant(None)

    def e_integer_literal(self, n):
        s = self.t(n).rstrip("uUlL").replace("_", "")
        return ast.Constant(int(s, 0))

    def e_real_literal(self, n):
        return ast.Constant(float(self.t(n).rstrip("fFdDmM").replace("_", "")))

    def e_string_literal(self, n):
        return ast.Constant(ast.literal_eval('"' + self.t(n)[1:-1] + '"'))

    def e_parenthesized_expression(self, n):
        return self.expr(n.named_children[0])

    def e_member_access_expression(self, n):
        return ast.Attribute(
            self.expr(n.child_by_field_name("expression")),
            self.t(n.child_by_field_name("name")),
            ast.Load(),
        )

    def e_predefined_type(self, n):
        return ast.Name(self.t(n), ast.Load())

    def args(self, n):
        return [self.expr(a.named_children[-1]) for a in n.named_children]

    def e_invocation_expression(self, n):
        return ast.Call(
            self.expr(n.child_by_field_name("function")),
            self.args(n.child_by_field_name("arguments")),
            [],
        )

    def e_object_creation_expression(self, n):
        a = n.child_by_field_name("arguments")
        return ast.Call(
            ast.Name(self.t(n.child_by_field_name("type")), ast.Load()),
            self.args(a) if a else [],
            [],
        )

    def e_element_access_expression(self, n):
        idx = self.args(n.child_by_field_name("subscript"))
        sl = idx[0] if len(idx) == 1 else ast.Tuple(idx, ast.Load())
        return ast.Subscript(
            self.expr(n.child_by_field_name("expression")), sl, ast.Load()
        )

    def e_conditional_expression(self, n):
        g = n.child_by_field_name
        return ast.IfExp(
            self.expr(g("condition")),
            self.expr(g("consequence")),
            self.expr(g("alternative")),
        )

    def e_cast_expression(self, n):
        ty = self.t(n.child_by_field_name("type"))
        v = self.expr(n.child_by_field_name("value"))
        if ty in ("int", "long", "short", "byte", "uint"):
            return ast.Call(ast.Name("int", ast.Load()), [v], [])
        return v

    def is_int(self, n):
        if n.type == "integer_literal":
            return True
        if n.type == "identifier":
            return self.types.get(self.t(n)) in ("int", "long", "uint", "short", "byte")
        if n.type == "parenthesized_expression":
            return self.is_int(n.named_children[0])
        if n.type == "cast_expression":
            return self.t(n.child_by_field_name("type")) in ("int", "long")
        if n.type == "binary_expression":
            return self.is_int(n.child_by_field_name("left")) and self.is_int(
                n.child_by_field_name("right")
            )
        return False

    def e_binary_expression(self, n):
        g = n.child_by_field_name
        op = self.t(g("operator"))
        l, r = self.expr(g("left")), self.expr(g("right"))
        if op in BOOLOPS:
            return ast.BoolOp(BOOLOPS[op](), [l, r])
        if op in CMPOPS:
            return ast.Compare(l, [CMPOPS[op]()], [r])
        if op == "/" and self.is_int(g("left")) and self.is_int(g("right")):
            return ast.Call(
                ast.Name("int", ast.Load()), [ast.BinOp(l, ast.Div(), r)], []
            )
        return ast.BinOp(l, BINOPS[op](), r)

    def e_prefix_unary_expression(self, n):
        op, operand = self.t(n.children[0]), n.children[1]
        if op in ("++", "--"):
            self.fail(n)
        return ast.UnaryOp(
            {"-": ast.USub, "+": ast.UAdd, "!": ast.Not, "~": ast.Invert}[op](),
            self.expr(operand),
        )

    def e_assignment_expression(self, n):
        self.fail(n)

    def s_expression_statement(self, n):
        e = n.named_children[0]
        if e.type == "assignment_expression":
            g = e.child_by_field_name
            op = self.t(g("operator"))
            target = self.expr(g("left"))
            target.ctx = ast.Store()
            val = self.expr(g("right"))
            if op == "=":
                return [ast.Assign([target], val)]
            return [ast.AugAssign(target, BINOPS[op[:-1]](), val)]
        if e.type in ("postfix_unary_expression", "prefix_unary_expression"):
            op = next(self.t(c) for c in e.children if self.t(c) in ("++", "--"))
            tgt = next(c for c in e.named_children)
            target = self.expr(tgt)
            target.ctx = ast.Store()
            return [
                ast.AugAssign(
                    target, ast.Add() if op == "++" else ast.Sub(), ast.Constant(1)
                )
            ]
        return [ast.Expr(self.expr(e))]

    def s_local_declaration_statement(self, n):
        decl = (
            n.named_children[-1]
            if n.named_children[-1].type == "variable_declaration"
            else n.named_children[0]
        )
        ty = self.t(decl.child_by_field_name("type"))
        out = []
        for d in decl.named_children[1:]:
            name = self.t(d.child_by_field_name("name") or d.named_children[0])
            self.types[name] = ty
            init = d.named_children[-1] if len(d.named_children) > 1 else None
            if init is not None and init.type == "equals_value_clause":
                init = init.named_children[-1]
            out.append(
                ast.Assign(
                    [ast.Name(name, ast.Store())],
                    self.expr(init) if init is not None else ast.Constant(None),
                )
            )
        return out

    def s_return_statement(self, n):
        return [
            ast.Return(self.expr(n.named_children[0]) if n.named_children else None)
        ]

    def s_break_statement(self, n):
        return [ast.Break()]

    def s_continue_statement(self, n):
        return [ast.Continue()]

    def s_block(self, n):
        return self.block(n)

    def s_yield_statement(self, n):
        # return []
        if n.named_children:
            return [ast.Expr(self.expr(n.named_children[0]))]
            # return [ast.Expr(ast.Yield(self.expr(n.named_children[0])))]
        return [ast.Return()]

    def s_if_statement(self, n):
        g = n.child_by_field_name
        alt = g("alternative")
        return [
            ast.If(
                self.expr(g("condition")),
                self.body(g("consequence")),
                self.body(alt) if alt else [],
            )
        ]

    def s_while_statement(self, n):
        g = n.child_by_field_name
        return [ast.While(self.expr(g("condition")), self.body(g("body")), [])]

    def s_for_statement(self, n):
        g = n.child_by_field_name
        out = []
        init = g("initializer")
        if init is not None:
            out += self.stmt_from_decl(init)

        cond = g("condition")
        updates = []
        for u in n.children_by_field_name("update"):
            updates += self.s_expression_statement_node(u)

        body = self.body(g("body"))
        body = self._insert_before_continue(body, updates)

        out.append(
            ast.While(
                self.expr(cond) if cond else ast.Constant(True),
                body + updates,
                [],
            )
        )
        return out

    def s_foreach_statement(self, n):
        g = n.child_by_field_name
        name = self.t(g("left"))
        ty = g("type")
        if ty is not None:
            self.types[name] = self.t(ty)
        return [
            ast.For(
                ast.Name(name, ast.Store()),
                self.expr(g("right")),
                self.body(g("body")),
                [],
            )
        ]

    def _insert_before_continue(self, stmts, updates):
        import copy

        result = []
        for s in stmts:
            if isinstance(s, ast.Continue):
                result += copy.deepcopy(updates)
                result.append(s)
            elif isinstance(s, (ast.While, ast.For)):
                result.append(s)
            else:
                for field in ("body", "orelse", "finalbody"):
                    if hasattr(s, field) and isinstance(getattr(s, field), list):
                        setattr(
                            s,
                            field,
                            self._insert_before_continue(getattr(s, field), updates),
                        )
                result.append(s)
        return result

    def stmt_from_decl(self, init):
        class Fake:
            named_children = [init]

        return self.s_local_declaration_statement(Fake)

    def s_expression_statement_node(self, expr_node):
        class Fake:
            named_children = [expr_node]

        return self.s_expression_statement(Fake)


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
ENUM_PREFIXES = {
    "FastNoiseLite.NoiseType.": "",
    "FastNoiseLite.FractalType.": "",
    "FastNoiseLite.CellularDistanceFunction.": "",
    "FastNoiseLite.CellularReturnType.": "",
}


def _fnl_to_gpu(pyfn):
    def branch_key(index, constructor_indent):
        for line_index in range(index - 1, -1, -1):
            line = lines[line_index]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent < constructor_indent and stripped.startswith(
                ("if ", "elif ", "else:")
            ):
                return line_index
        return None

    gpu_properties = {
        "SetNoiseType": "type",
        "SetFractalType": "fractal",
        "SetFrequency": "freq",
        "SetFractalOctaves": "octaves",
        "SetFractalLacunarity": "lacunarity",
        "SetFractalGain": "gain",
        "SetFractalWeightedStrength": "weighted",
        "SetCellularJitter": "jitter",
    }
    enum_names = {
        "NoiseType": {
            "OpenSimplex2": "OPENSIMPLEX2",
            "Perlin": "PERLIN",
            "Value": "VALUE",
            "Cellular": "CELLULAR",
        },
        "FractalType": {
            "None": "NONE",
            "FBm": "FBM",
            "Ridged": "RIDGED",
            "PingPong": "PINGPONG",
        },
    }

    lines = pyfn.splitlines()
    constructors = []
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)(\w+)\s*=\s*FastNoiseLite\((.*)\)\s*$", line)
        if match:
            indent, var, seed = match.groups()
            constructors.append(
                {
                    "index": index,
                    "indent": len(indent),
                    "var": var,
                    "seed": seed,
                    "branch": None,
                    "setters": [],
                }
            )

    if not constructors:
        return pyfn

    for constructor in constructors:
        constructor["branch"] = branch_key(constructor["index"], constructor["indent"])

    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)(\w+)\.(Set\w+)\((.*)\)\s*$", line)
        if not match:
            continue
        _, var, setter, value = match.groups()
        candidates = [
            constructor
            for constructor in constructors
            if constructor["var"] == var
            and constructor["index"] < index
            and constructor["branch"] == branch_key(index, constructor["indent"])
        ]
        if candidates:
            candidates[-1]["setters"].append(
                (index, len(match.group(1)), setter, value)
            )

    def enum_value(value):
        match = re.fullmatch(
            r"FastNoiseLite\.(NoiseType|FractalType)\.(\w+)", value.strip()
        )
        if match:
            name = enum_names[match.group(1)].get(match.group(2), value)
            return f"pyglslfnl.{name}"
        return value

    def enclosing_loop(index, indent):
        candidate = None
        for loop_index in range(index - 1, -1, -1):
            stripped = lines[loop_index].lstrip()
            if len(lines[loop_index]) - len(stripped) < indent and stripped.startswith(
                ("while ", "for ")
            ):
                if (
                    candidate is None
                    or len(lines[loop_index]) - len(stripped) < candidate[0]
                ):
                    candidate = (len(lines[loop_index]) - len(stripped), loop_index)
        return candidate[1] if candidate is not None else None

    replacements = {}
    insertions = {}
    removed = set()
    for constructor in constructors:
        var = constructor["var"]
        constructor_index = constructor["index"]
        constructor_indent = constructor["indent"]
        seed = constructor["seed"]
        replacements[constructor_index] = (
            f"{' ' * constructor_indent}{var}_seed = {seed}"
        )
        config = []
        dynamic_setter = None
        for index, indent, setter, value in constructor["setters"]:
            removed.add(index)
            property_name = gpu_properties.get(setter)
            if property_name is None:
                continue
            value = enum_value(value)
            config.append((property_name, value))
            if setter == "SetFrequency" and enclosing_loop(index, indent) is not None:
                dynamic_setter = (index, indent, value)

        if not config:
            continue
        kwargs = []
        for property_name, value in config:
            if property_name == "freq" and dynamic_setter is not None:
                continue
            kwargs.append(f"{property_name}={value}")

        if dynamic_setter is None:
            target = constructor["setters"][-1][0] + 1
            frequency = next((value for name, value in config if name == "freq"), None)
        else:
            _, dynamic_indent, frequency = dynamic_setter
            target = enclosing_loop(dynamic_setter[0], dynamic_indent)
            if target is None:
                target = dynamic_setter[0] + 1
            if "GetNoise" in frequency:
                frequency = re.sub(r"(\w+)\.GetNoise\(\w+,\s*\w+\)", r"\1", frequency)
            else:
                loop_variable = re.search(r"\b(\w+)\s*/\s*height", frequency)
                if loop_variable:
                    frequency = frequency.replace(
                        loop_variable.group(1),
                        "np.broadcast_to(np.arange(height)[None, :], (width, height))",
                    )
            kwargs.append(f"freq={frequency}")

        call = f"pyglslfnl.noise(width, height, {var}_seed"
        if kwargs:
            call += ", " + ", ".join(kwargs)
        call += ")"
        indent = len(lines[target]) - len(lines[target].lstrip())
        insertions.setdefault(target, []).append(f"{' ' * indent}{var} = {call}")

    output = []
    for index, line in enumerate(lines):
        if index in insertions:
            output.extend(insertions[index])
        if index in removed:
            continue
        line = replacements.get(index, line)
        line = re.sub(r"(\w+)\.GetNoise\(([^,]+),\s*([^\)]+)\)", r"\1[\2, \3]", line)
        output.append(line)

    return "\n".join(output)


def transpile_method(method_node, as_function=False):
    """note to self, use getfunc_as_tree"""
    tp = Transpiler()
    name = tp.t(method_node.child_by_field_name("name"))
    params = []
    for p in method_node.child_by_field_name("parameters").named_children:
        pn = tp.t(p.child_by_field_name("name"))
        tp.types[pn] = tp.t(p.child_by_field_name("type"))
        params.append(ast.arg(pn))
    body = tp.block(method_node.child_by_field_name("body"))

    if as_function:
        fn = ast.FunctionDef(
            name, ast.arguments([], params, None, [], [], None, []), body, [], None
        )
        mod = ast.fix_missing_locations(ast.Module([fn], []))
    else:
        mod = ast.fix_missing_locations(ast.Module(body, []))

    tx = re.sub(r"<(\S*?)>", r"(\1)", ast.unparse(mod))
    # for k, v in (PROPERTY_MAP | ENUM_PREFIXES).items():
    #     tx = tx.replace(k, v)
    # tx = tx.replace("UnityEngine.Random", "Random")
    tx = tx.replace("return", "exit()")
    tx = _fnl_to_gpu(tx)
    tx = re.sub(r"^\s*None\s*$", "", tx, flags=re.MULTILINE)

    return "\n".join([line for line in tx.splitlines() if "tileCounter" not in line])


def transpile_module(module, skip_unsupported=False, as_function=True):
    from cparser.csfunc import getmodule_methods_as_tree

    transpiled = {}
    for method_node in getmodule_methods_as_tree(module):
        name = method_node.child_by_field_name("name").text.decode("utf-8")
        try:
            source = transpile_method(method_node, as_function=as_function)
        except Exception:
            if not skip_unsupported:
                raise
            continue
        transpiled.setdefault(name, []).append(source)
    return transpiled
