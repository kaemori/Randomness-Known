from cparser.transpiler import transpile
from cparser.ir_nodes import (
    Block,
    IfChain,
    ForLoop,
    NoiseConstruct,
    NoiseConfigure,
    WorldBlockAssign,
    ExprStmt,
    YieldReturn,
    VarDecl,
)
from cparser.expr_parser import find_embedded_calls, RandomCall, NoiseCall
from dataclasses import asdict


def collect_exprs(stmt):
    if isinstance(stmt, Block):
        for s in stmt.body:
            yield from collect_exprs(s)
    elif isinstance(stmt, IfChain):
        for arm in stmt.arms:
            if arm.condition is not None:
                yield arm.condition
            yield from collect_exprs(arm.body)
    elif isinstance(stmt, ForLoop):
        yield stmt.condition
        if stmt.init:
            yield from collect_exprs(stmt.init)
        if stmt.update:
            yield from collect_exprs(stmt.update)
        yield from collect_exprs(stmt.body)
    elif isinstance(stmt, NoiseConstruct):
        yield stmt.seed
        for s in stmt.settings:
            for a in s.args:
                yield a
    elif isinstance(stmt, NoiseConfigure):
        for a in stmt.setting.args:
            yield a
    elif isinstance(stmt, WorldBlockAssign):
        yield stmt.x
        yield stmt.y
        yield stmt.value
    elif isinstance(stmt, VarDecl):
        yield stmt.value
    elif isinstance(stmt, ExprStmt):
        yield stmt.expr
    elif isinstance(stmt, YieldReturn):
        if stmt.value:
            yield stmt.value


def stats_for(stmt):
    noise_constructs = 0
    noise_configures = 0
    world_block_writes = 0
    random_calls = 0
    noise_calls = 0

    def walk(s):
        nonlocal noise_constructs, noise_configures, world_block_writes
        if isinstance(s, Block):
            for c in s.body:
                walk(c)
        elif isinstance(s, IfChain):
            for arm in s.arms:
                walk(arm.body)
        elif isinstance(s, ForLoop):
            walk(s.body)
        elif isinstance(s, NoiseConstruct):
            noise_constructs += 1
        elif isinstance(s, NoiseConfigure):
            noise_configures += 1
        elif isinstance(s, WorldBlockAssign):
            world_block_writes += 1

    walk(stmt)

    for e in collect_exprs(stmt):
        for call in find_embedded_calls(e):
            if isinstance(call, RandomCall):
                random_calls += 1
            elif isinstance(call, NoiseCall):
                noise_calls += 1

    return dict(
        noise_constructs=noise_constructs,
        noise_configures=noise_configures,
        world_block_writes=world_block_writes,
        random_calls=random_calls,
        noise_calls=noise_calls,
    )


def main():
    with open("terr_ir.cs") as f:
        lines = f.read().split("\n")
    ir = transpile(lines)

    with open("terr_ir.ir", "w") as f:
        import json

        # json.dump(asdict(ir), f, indent=4)
        print(ir, file=f)


if __name__ == "__main__":
    main()
