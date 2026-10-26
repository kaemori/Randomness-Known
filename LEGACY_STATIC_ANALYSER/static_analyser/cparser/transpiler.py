from __future__ import annotations
import re
from typing import Optional
from cparser.ir_nodes import (
    Stmt,
    Block,
    IfChain,
    IfBranch,
    ForLoop,
    VarDecl,
    NoiseConstruct,
    NoiseSetting,
    NoiseConfigure,
    WorldBlockAssign,
    ExprStmt,
    YieldReturn,
    YieldBreak,
    FunctionIR,
)
from cparser.expr_parser import parse_expr, split_top_level_args

IDENT = "[A-Za-z_][A-Za-z0-9_]*"
KNOWN_TYPES = {
    "int",
    "float",
    "double",
    "bool",
    "byte",
    "short",
    "long",
    "ushort",
    "ulong",
    "string",
    "var",
    "Vector2Int",
    "Vector2",
    "Vector3",
    "FastNoiseLite",
    "GameObject",
}
TYPE_RE = (
    "(?:"
    + "|".join(re.escape(t) for t in KNOWN_TYPES)
    + f"|List<[^>]+>|Dictionary<[^>]+>|{IDENT}(?:\\[\\])?)"
)
RE_NOISE_NEW = re.compile(
    f"^FastNoiseLite\\s+({IDENT})\\s*=\\s*new\\s+FastNoiseLite\\s*\\((.*)\\)\\s*;?$"
)
RE_NOISE_SET_CHAIN = re.compile(f"^({IDENT})\\.(Set{IDENT})\\s*\\((.*)\\)\\s*;$")
NON_NOISE_OWNERS = {"this", "Object", "Resources", "Quaternion"}
RE_WORLDBLOCK_ASSIGN = re.compile(
    "^this\\.worldBlocks\\s*\\[\\s*(.*?)\\s*,\\s*(.*?)\\s*\\]\\s*=\\s*(.*);$", re.DOTALL
)
RE_YIELD_RETURN = re.compile("^yield\\s+return\\s+(.*?)\\s*;$")
RE_YIELD_BREAK = re.compile("^yield\\s+break\\s*;$")
RE_IF = re.compile("^if\\s*\\((.*)\\)\\s*\\{?$", re.DOTALL)
RE_ELSE_IF = re.compile("^else\\s+if\\s*\\((.*)\\)\\s*\\{?$", re.DOTALL)
RE_ELSE = re.compile("^else\\s*\\{?$")
RE_FOR = re.compile("^for\\s*\\((.*)\\)\\s*\\{?$", re.DOTALL)
RE_PLAIN_ASSIGN = re.compile(
    f"^({IDENT})\\s*(\\+=|-=|\\*=|/=|=)\\s*(.*)\\s*;$", re.DOTALL
)
RE_TYPED_DECL = re.compile(f"^({TYPE_RE})\\s+({IDENT})\\s*(=)\\s*(.*)\\s*;$", re.DOTALL)
RE_TYPED_DECL_NO_INIT = re.compile(f"^({TYPE_RE})\\s+({IDENT})\\s*;$")
RE_INCDEC = re.compile(f"^({IDENT})\\s*(\\+\\+|--)\\s*;$")
RE_PRE_INCDEC = re.compile(f"^(\\+\\+|--)\\s*({IDENT})\\s*;$")
RE_EXPR_STMT = re.compile("^(.*)\\s*;$", re.DOTALL)


def tokenize_statements(lines):
    stmts = []
    buf = []
    start_line = None
    depth = 0
    in_str = False

    def flush():
        nonlocal buf, start_line
        text = " ".join(buf).strip()
        text = re.sub("\\s+", " ", text)
        if text:
            stmts.append((text, start_line))
        buf = []
        start_line = None

    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if line == "":
            continue
        if line == "{" and depth == 0 and not buf:
            stmts.append(("{", i))
            continue
        if line == "}" and depth == 0 and not buf:
            stmts.append(("}", i))
            continue
        if start_line is None:
            start_line = i
        buf.append(line)
        j = 0
        while j < len(line):
            ch = line[j]
            if in_str:
                if ch == '"' and line[j - 1 : j] != "\\":
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            j += 1
        stripped_concat = " ".join(buf)
        if depth == 0:
            if line.rstrip().endswith(";"):
                flush()
                continue
            if line.rstrip().endswith("{"):
                flush()
                continue
    if buf:
        flush()
    return stmts


class Parser:
    def __init__(self, stmts):
        self.stmts = stmts
        self.pos = 0

    def peek(self):
        return self.stmts[self.pos] if self.pos < len(self.stmts) else None

    def advance(self):
        tok = self.stmts[self.pos]
        self.pos += 1
        return tok

    def expect_open_brace(self):
        tok = self.peek()
        if tok and tok[0] == "{":
            self.advance()

    def parse_block_until_close(self):
        block = Block(body=[])
        while True:
            tok = self.peek()
            if tok is None:
                break
            text, line_no = tok
            if text == "}":
                self.advance()
                break
            stmt = self.parse_one_statement()
            if stmt is not None:
                block.body.append(stmt)
        return block

    def parse_one_statement(self):
        text, line_no = self.advance()
        if text == "{":
            inner = self.parse_block_until_close()
            return inner
        m = RE_IF.match(text)
        if m:
            return self._parse_if_chain(m.group(1), line_no, text)
        m = RE_FOR.match(text)
        if m:
            return self._parse_for(m.group(1), line_no, text)
        m = RE_YIELD_RETURN.match(text)
        if m:
            val_text = m.group(1).strip()
            value = None if val_text in ("", "null") else parse_expr(val_text)
            return YieldReturn(line_no=line_no, value=value)
        if RE_YIELD_BREAK.match(text):
            return YieldBreak(line_no=line_no)
        m = RE_NOISE_NEW.match(text)
        if m:
            name, seed_text = m.group(1), m.group(2)
            node = NoiseConstruct(
                line_no=line_no, name=name, seed=parse_expr(seed_text), settings=[]
            )
            while True:
                nxt = self.peek()
                if nxt is None:
                    break
                ntext, nline = nxt
                sm = RE_NOISE_SET_CHAIN.match(ntext)
                if sm and sm.group(1) == name:
                    self.advance()
                    args = [parse_expr(a) for a in split_top_level_args(sm.group(3))]
                    node.settings.append(
                        NoiseSetting(
                            noise_var=name, method=sm.group(2), args=args, line_no=nline
                        )
                    )
                else:
                    break
            return node
        m = RE_NOISE_SET_CHAIN.match(text)
        if m and m.group(1) not in NON_NOISE_OWNERS:
            noise_var, method, argstr = m.group(1), m.group(2), m.group(3)
            args = [parse_expr(a) for a in split_top_level_args(argstr)]
            return NoiseConfigure(
                line_no=line_no,
                noise_var=noise_var,
                setting=NoiseSetting(
                    noise_var=noise_var, method=method, args=args, line_no=line_no
                ),
            )
        m = RE_WORLDBLOCK_ASSIGN.match(text)
        if m:
            x_text, y_text, val_text = m.group(1), m.group(2), m.group(3)
            return WorldBlockAssign(
                line_no=line_no,
                x=parse_expr(x_text),
                y=parse_expr(y_text),
                value=parse_expr(val_text),
            )
        m = RE_INCDEC.match(text)
        if m:
            name, op = m.group(1), m.group(2)
            return VarDecl(
                line_no=line_no,
                name=name,
                var_type=None,
                value=parse_expr(name),
                is_declaration=False,
                compound_op=op,
            )
        m = RE_PRE_INCDEC.match(text)
        if m:
            op, name = m.group(1), m.group(2)
            return VarDecl(
                line_no=line_no,
                name=name,
                var_type=None,
                value=parse_expr(name),
                is_declaration=False,
                compound_op=op,
            )
        m = RE_TYPED_DECL.match(text)
        if m:
            type_text, name, op, val_text = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4),
            )
            return VarDecl(
                line_no=line_no,
                name=name,
                var_type=type_text,
                value=parse_expr(val_text),
                is_declaration=True,
                compound_op=None,
            )
        m = RE_TYPED_DECL_NO_INIT.match(text)
        if m:
            type_text, name = m.group(1), m.group(2)
            return VarDecl(
                line_no=line_no,
                name=name,
                var_type=type_text,
                value=None,
                is_declaration=True,
                compound_op=None,
            )
        m = RE_PLAIN_ASSIGN.match(text)
        if m:
            name, op, val_text = m.group(1), m.group(2), m.group(3)
            return VarDecl(
                line_no=line_no,
                name=name,
                var_type=None,
                value=parse_expr(val_text),
                is_declaration=False,
                compound_op=None if op == "=" else op,
            )
        m = RE_EXPR_STMT.match(text)
        if m:
            inner = m.group(1).strip()
            return ExprStmt(line_no=line_no, expr=parse_expr(inner))
        return ExprStmt(line_no=line_no, expr=parse_expr(text))

    def _parse_if_chain(self, cond_text, line_no, header_text):
        chain = IfChain(line_no=line_no, arms=[])
        had_open_brace = header_text.rstrip().endswith("{")
        body = self._parse_branch_body(had_open_brace)
        chain.arms.append(IfBranch(condition=parse_expr(cond_text), body=body))
        while True:
            tok = self.peek()
            if tok is None:
                break
            ttext, tline = tok
            m = RE_ELSE_IF.match(ttext)
            if m:
                self.advance()
                had_open = ttext.rstrip().endswith("{")
                b = self._parse_branch_body(had_open)
                chain.arms.append(IfBranch(condition=parse_expr(m.group(1)), body=b))
                continue
            if RE_ELSE.match(ttext):
                self.advance()
                had_open = ttext.rstrip().endswith("{")
                b = self._parse_branch_body(had_open)
                chain.arms.append(IfBranch(condition=None, body=b))
                continue
            break
        return chain

    def _parse_branch_body(self, had_open_brace):
        if had_open_brace:
            return self.parse_block_until_close()
        tok = self.peek()
        if tok and tok[0] == "{":
            self.advance()
            return self.parse_block_until_close()
        stmt = self.parse_one_statement()
        return Block(body=[stmt] if stmt else [])

    def _parse_for(self, header_text, line_no, full_header):
        parts = header_text.split(";")
        init_text = parts[0].strip() if len(parts) > 0 else ""
        cond_text = parts[1].strip() if len(parts) > 1 else ""
        update_text = parts[2].strip() if len(parts) > 2 else ""
        init_stmt = self._parse_inline_small_stmt(init_text) if init_text else None
        update_stmt = (
            self._parse_inline_small_stmt(update_text) if update_text else None
        )
        condition = parse_expr(cond_text) if cond_text else RawExprTrue()
        had_open_brace = full_header.rstrip().endswith("{")
        body = self._parse_branch_body(had_open_brace)
        return ForLoop(
            line_no=line_no,
            init=init_stmt,
            condition=condition,
            update=update_stmt,
            body=body,
        )

    def _parse_inline_small_stmt(self, text):
        m = RE_INCDEC.match(text + ";")
        if m:
            return VarDecl(
                name=m.group(1),
                var_type=None,
                value=parse_expr(m.group(1)),
                is_declaration=False,
                compound_op=m.group(2),
            )
        m = RE_TYPED_DECL.match(text + ";")
        if m:
            type_text, name, op, val_text = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4),
            )
            return VarDecl(
                name=name,
                var_type=type_text,
                value=parse_expr(val_text),
                is_declaration=True,
                compound_op=None,
            )
        m = RE_TYPED_DECL_NO_INIT.match(text + ";")
        if m:
            type_text, name = m.group(1), m.group(2)
            return VarDecl(
                name=name,
                var_type=type_text,
                value=None,
                is_declaration=True,
                compound_op=None,
            )
        m = RE_PLAIN_ASSIGN.match(text + ";")
        if m:
            name, op, val_text = m.group(1), m.group(2), m.group(3)
            return VarDecl(
                name=name,
                var_type=None,
                value=parse_expr(val_text),
                is_declaration=False,
                compound_op=None if op == "=" else op,
            )
        return ExprStmt(expr=parse_expr(text))


def RawExprTrue():
    from ir_nodes import RawExpr

    return RawExpr(raw="true")


def transpile(lines, func_name, is_coroutine=True):
    lines = list(lines)
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx < len(lines) and re.search(
        "\\b" + re.escape(func_name) + "\\s*\\(", lines[idx]
    ):
        idx += 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "{":
            idx += 1
    body_lines = lines[idx:]
    j = len(body_lines) - 1
    while j >= 0 and body_lines[j].strip() == "":
        j -= 1
    if j >= 0 and body_lines[j].strip() == "}":
        body_lines = body_lines[:j]
    stmts = tokenize_statements(body_lines)
    parser = Parser(stmts)
    block = parser.parse_block_until_close() if False else _parse_top_level(parser)
    return FunctionIR(name=func_name, is_coroutine=is_coroutine, body=block)


def _parse_top_level(parser):
    block = Block(body=[])
    while parser.peek() is not None:
        stmt = parser.parse_one_statement()
        if stmt is not None:
            block.body.append(stmt)
    return block
