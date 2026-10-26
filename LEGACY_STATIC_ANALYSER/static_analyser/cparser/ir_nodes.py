from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Union


@dataclass(kw_only=True)
class Expr:
    raw: str


@dataclass(kw_only=True)
class RawExpr(Expr):
    pass


@dataclass(kw_only=True)
class RandomCall(Expr):
    member: str
    args: list[Expr] = field(default_factory=list)


@dataclass(kw_only=True)
class NoiseCall(Expr):
    noise_var: str
    args: list[Expr] = field(default_factory=list)


@dataclass(kw_only=True)
class MethodCall(Expr):
    target: str
    args: list[Expr] = field(default_factory=list)
    type_args: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class ConstructorCall(Expr):
    type_name: str
    args: list[Expr] = field(default_factory=list)


@dataclass(kw_only=True)
class Vector2Node(Expr):
    kind: str
    x: Expr = None
    y: Expr = None


@dataclass(kw_only=True)
class Vector3Node(Expr):
    kind: str
    x: Expr = None
    y: Expr = None
    z: Expr = None


@dataclass(kw_only=True)
class Stmt:
    line_no: int = -1


@dataclass(kw_only=True)
class VarDecl(Stmt):
    name: str
    var_type: Optional[str]
    value: Optional[Expr]
    is_declaration: bool = False
    compound_op: Optional[str] = None


@dataclass(kw_only=True)
class NoiseConstruct(Stmt):
    name: str
    seed: Expr
    settings: list["NoiseSetting"] = field(default_factory=list)


@dataclass(kw_only=True)
class NoiseSetting:
    noise_var: str
    method: str
    args: list[Expr] = field(default_factory=list)
    line_no: int = -1


@dataclass(kw_only=True)
class NoiseConfigure(Stmt):
    noise_var: str
    setting: NoiseSetting


@dataclass(kw_only=True)
class WorldBlockAssign(Stmt):
    x: Expr
    y: Expr
    value: Expr


@dataclass(kw_only=True)
class ExprStmt(Stmt):
    expr: Expr


@dataclass(kw_only=True)
class YieldReturn(Stmt):
    value: Optional[Expr]


@dataclass(kw_only=True)
class YieldBreak(Stmt):
    pass


@dataclass(kw_only=True)
class Block(Stmt):
    body: list[Stmt] = field(default_factory=list)


@dataclass(kw_only=True)
class ForLoop(Stmt):
    init: Optional[Stmt]
    condition: Expr
    update: Optional[Stmt]
    body: Block = field(default_factory=Block)


@dataclass(kw_only=True)
class IfBranch:
    condition: Optional[Expr]
    body: Block


@dataclass(kw_only=True)
class IfChain(Stmt):
    arms: list[IfBranch] = field(default_factory=list)


@dataclass(kw_only=True)
class FunctionIR:
    name: str
    is_coroutine: bool
    body: Block
