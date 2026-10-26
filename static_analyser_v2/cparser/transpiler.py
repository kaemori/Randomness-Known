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
        return []
        # if n.named_children:
        #     return [ast.Expr(ast.Yield(self.expr(n.named_children[0])))]
        # return [ast.Return()]

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

    return re.sub(r"<(\S*?)>", r"(\1)", ast.unparse(mod))
