from __future__ import annotations
from ir_nodes import (
    Block,
    IfChain,
    ForLoop,
    VarDecl,
    NoiseConstruct,
    NoiseConfigure,
    WorldBlockAssign,
    ExprStmt,
    YieldReturn,
    YieldBreak,
    FunctionIR,
)


def _e(expr):
    if expr is None:
        return "null"
    return expr.raw


def print_ir(func):
    kind = "coroutine" if func.is_coroutine else "function"
    print(f"{kind} {func.name}()")
    _print_block(func.body, 1)


def _ind(level):
    return "  " * level


def _print_block(block, level):
    for stmt in block.body:
        _print_stmt(stmt, level)


def _print_stmt(stmt, level):
    pad = _ind(level)
    ln = f"  # L{stmt.line_no}" if getattr(stmt, "line_no", -1) != -1 else ""
    if isinstance(stmt, NoiseConstruct):
        print(
            f"{pad}NoiseConstruct {stmt.name} = FastNoiseLite(seed={_e(stmt.seed)}){ln}"
        )
        for s in stmt.settings:
            print(
                f"{pad}  .{s.method}({", ".join(_e(a)for a in s.args)})  # L{s.line_no}"
            )
    elif isinstance(stmt, NoiseConfigure):
        s = stmt.setting
        print(
            f"{pad}NoiseConfigure {stmt.noise_var}.{s.method}({", ".join(_e(a)for a in s.args)}){ln}"
        )
    elif isinstance(stmt, WorldBlockAssign):
        print(
            f"{pad}WorldBlockAssign worldBlocks[{_e(stmt.x)}, {_e(stmt.y)}] = {_e(stmt.value)}{ln}"
        )
    elif isinstance(stmt, VarDecl):
        kind = "decl" if stmt.is_declaration else "assign"
        t = f"{stmt.var_type} " if stmt.var_type else ""
        op = stmt.compound_op or "="
        print(f"{pad}VarDecl[{kind}] {t}{stmt.name} {op} {_e(stmt.value)}{ln}")
    elif isinstance(stmt, YieldReturn):
        print(f"{pad}YieldReturn {_e(stmt.value)if stmt.value else"null"}{ln}")
    elif isinstance(stmt, YieldBreak):
        print(f"{pad}YieldBreak{ln}")
    elif isinstance(stmt, ExprStmt):
        print(f"{pad}ExprStmt {_e(stmt.expr)}{ln}")
    elif isinstance(stmt, ForLoop):
        init = _stmt_oneline(stmt.init) if stmt.init else ""
        upd = _stmt_oneline(stmt.update) if stmt.update else ""
        print(f"{pad}ForLoop ({init}; {_e(stmt.condition)}; {upd}){ln}")
        _print_block(stmt.body, level + 1)
    elif isinstance(stmt, IfChain):
        print(f"{pad}IfChain{ln}")
        for i, arm in enumerate(stmt.arms):
            label = "if" if i == 0 else "else" if arm.condition is None else "else if"
            cond = f"({_e(arm.condition)})" if arm.condition is not None else ""
            print(f"{pad}  {label}{cond}:")
            _print_block(arm.body, level + 2)
    elif isinstance(stmt, Block):
        _print_block(stmt, level)
    else:
        print(f"{pad}<unknown stmt {type(stmt).__name__}>{ln}")


def _stmt_oneline(stmt):
    if isinstance(stmt, VarDecl):
        if stmt.compound_op in ("++", "--"):
            return f"{stmt.name}{stmt.compound_op}"
        t = f"{stmt.var_type} " if stmt.var_type else ""
        op = stmt.compound_op or "="
        return f"{t}{stmt.name} {op} {_e(stmt.value)}"
    if isinstance(stmt, ExprStmt):
        return _e(stmt.expr)
    return str(stmt)
