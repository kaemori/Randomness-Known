from __future__ import annotations

import re
from typing import Optional

from cparser.ir_nodes import (
    Expr,
    RawExpr,
    RandomCall,
    NoiseCall,
    MethodCall,
    ConstructorCall,
    Vector2Node,
    Vector3Node,
)

CAST_RE = re.compile(r"^\((ushort|long|int|float|double|byte|short)\)\s*")
IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
TARGET_RE = re.compile(
    rf"^((?:this\.)?{IDENT}(?:\.{IDENT})*)" rf"(?:<([^>]*)>)?" r"\s*\(\s*(.*)\s*\)$",
    re.DOTALL,
)

NEW_VEC_RE = re.compile(
    rf"^new\s+(Vector2Int|Vector2|Vector3)\s*\(\s*(.*)\s*\)$", re.DOTALL
)
NEW_CONSTRUCTOR_RE = re.compile(
    rf"^new\s+({IDENT}(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(\s*(.*)\s*\)$",
    re.DOTALL,
)


def split_top_level_args(s: str) -> list[str]:
    parts = []
    depth = 0
    buf = []
    in_str = False
    for ch in s:
        if in_str:
            buf.append(ch)
            if ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            continue
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail or parts:
        parts.append(tail)
    return [p for p in parts if p != ""]


def _strip_outer_parens(s: str) -> str:
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        depth = 0
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    return s
        return s[1:-1].strip()
    return s


def parse_expr(text: str) -> Expr:
    original = text.strip()
    s = original

    m = CAST_RE.match(s)
    if m:
        inner = parse_expr(s[m.end() :])
        inner.raw = original
        return inner

    s2 = _strip_outer_parens(s)
    if s2 != s:
        inner = parse_expr(s2)
        inner.raw = original
        return inner

    if s == "Random.value":
        return RandomCall(raw=original, member="value", args=[])

    m = NEW_VEC_RE.match(s)
    if m:
        kind, argstr = m.group(1), m.group(2)
        parts = [parse_expr(p) for p in split_top_level_args(argstr)]
        if kind == "Vector3":
            x = parts[0] if len(parts) > 0 else None
            y = parts[1] if len(parts) > 1 else None
            z = parts[2] if len(parts) > 2 else None
            return Vector3Node(raw=original, kind=kind, x=x, y=y, z=z)
        else:
            x = parts[0] if len(parts) > 0 else None
            y = parts[1] if len(parts) > 1 else None
            return Vector2Node(raw=original, kind=kind, x=x, y=y)

    m = NEW_CONSTRUCTOR_RE.match(s)
    if m:
        type_name, argstr = m.group(1), m.group(2)
        return ConstructorCall(
            raw=original,
            type_name=type_name,
            args=[parse_expr(p) for p in split_top_level_args(argstr)],
        )

    m = TARGET_RE.match(s)
    if m:
        target_full, type_args_str, argstr = m.group(1), m.group(2), m.group(3)
        args = [parse_expr(p) for p in split_top_level_args(argstr)]
        type_args = (
            [t.strip() for t in type_args_str.split(",")] if type_args_str else []
        )

        if "." in target_full:
            owner, member = target_full.rsplit(".", 1)
        else:
            owner, member = "", target_full

        if owner == "Random" and member == "Range":
            return RandomCall(raw=original, member="Range", args=args)

        if member == "GetNoise":
            return NoiseCall(raw=original, noise_var=owner, args=args)

        return MethodCall(
            raw=original, target=target_full, args=args, type_args=type_args
        )

    return RawExpr(raw=original)


CALL_HEAD_RE = re.compile(rf"{IDENT}(?:\.{IDENT})*\s*\(")


def _scan_calls_in_text(text: str) -> list[Expr]:
    results = []
    i = 0
    n = len(text)
    while i < n:
        m = CALL_HEAD_RE.match(text, i)
        if not m:
            i += 1
            continue
        open_paren = m.end() - 1
        depth = 0
        j = open_paren
        while j < n:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            print(f"unbalanced parens in text: {text}")
            break
        call_text = text[m.start() : j + 1]
        parsed = parse_expr(call_text)
        results.append(parsed)
        i = j + 1
    return results


def find_embedded_calls(expr: Expr) -> list[Expr]:
    found: list[Expr] = []

    def walk(e: Expr):
        if isinstance(e, RandomCall):
            found.append(e)
            for a in e.args:
                walk(a)
        elif isinstance(e, NoiseCall):
            found.append(e)
            for a in e.args:
                walk(a)
        elif isinstance(e, MethodCall):
            for a in e.args:
                walk(a)
        elif isinstance(e, (Vector2Node,)):
            if e.x:
                walk(e.x)
            if e.y:
                walk(e.y)
        elif isinstance(e, (Vector3Node,)):
            if e.x:
                walk(e.x)
            if e.y:
                walk(e.y)
            if e.z:
                walk(e.z)
        elif isinstance(e, RawExpr):
            for parsed in _scan_calls_in_text(e.raw):
                if isinstance(parsed, (RandomCall, NoiseCall)):
                    found.append(parsed)
                    for a in parsed.args:
                        walk(a)
            if re.search(r"(?<![\w.])Random\.value(?!\w)", e.raw):
                found.append(RandomCall(raw="Random.value", member="value", args=[]))

    walk(expr)
    return found
