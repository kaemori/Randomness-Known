import textwrap
import ast


class ExitCleaner(ast.NodeTransformer):
    def __init__(self):
        self.depth = 0

    @staticmethod
    def _is_exit_call(stmt):
        return (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "exit"
        )

    def _clean_body(self, body):
        cleaned = []

        for stmt in body:
            if self._is_exit_call(stmt):
                if self.depth > 0:
                    print(
                        f"warning: exit() found at depth {self.depth} "
                        f"(line {stmt.lineno}), not in the main branch; "
                        f"trimming {len(body) - len(cleaned)} trailing "
                        f"statement(s) in this block"
                    )
                break

            cleaned.append(self.visit(stmt))

        return cleaned

    def visit_Module(self, node):
        node.body = self._clean_body(node.body)
        return node

    def _visit_block_owner(self, node):
        self.depth += 1
        node.body = self._clean_body(node.body)
        if getattr(node, "orelse", None):
            node.orelse = self._clean_body(node.orelse)
        if getattr(node, "finalbody", None):
            node.finalbody = self._clean_body(node.finalbody)
        self.depth -= 1
        return node

    visit_If = _visit_block_owner
    visit_While = _visit_block_owner
    visit_For = _visit_block_owner
    visit_Try = _visit_block_owner
    visit_With = _visit_block_owner
    visit_FunctionDef = _visit_block_owner
    visit_ClassDef = _visit_block_owner


def clean_exits(pycode):
    tree = ast.parse(pycode)
    tree = ExitCleaner().visit(tree)
    tree = ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def dirty_exit(pycode):
    return f"try:\n{textwrap.indent(pycode, "    ")}\nexcept SystemExit:\n    pass"
