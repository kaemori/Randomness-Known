# cuz regex wasnt good enough...

_BREAK_CHARS = set(",;")
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {v: k for (k, v) in _OPEN.items()}


def _fix_ternary_once(code):
    depth_stack = []
    last_break = {0: 0}
    break_is_open = {0: False}
    in_str = None
    i = 0
    n = len(code)
    while i < n:
        ch = code[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            i += 1
            continue
        depth = len(depth_stack)
        if ch in _OPEN:
            depth_stack.append(ch)
            last_break[depth + 1] = i + 1
            break_is_open[depth + 1] = True
            i += 1
            continue
        if ch in _CLOSE:
            if depth_stack and _OPEN[depth_stack[-1]] == ch:
                depth_stack.pop()
            i += 1
            continue
        if ch in _BREAK_CHARS:
            last_break[depth] = i + 1
            break_is_open[depth] = False
            i += 1
            continue
        if ch == "?" and code[i : i + 2] not in ("?.", "??"):
            cond_start = last_break.get(depth, 0)
            q_pos = i
            counter = 1
            j = i + 1
            j_in_str = None
            j_depth = 0
            colon_pos = None
            while j < n:
                cj = code[j]
                if j_in_str:
                    if cj == "\\":
                        j += 2
                        continue
                    if cj == j_in_str:
                        j_in_str = None
                    j += 1
                    continue
                if cj in ('"', "'", "`"):
                    j_in_str = cj
                    j += 1
                    continue
                if cj in _OPEN:
                    j_depth += 1
                elif cj in _CLOSE:
                    j_depth -= 1
                elif j_depth == 0:
                    if cj == "?" and code[j : j + 2] not in ("?.", "??"):
                        counter += 1
                    elif (
                        cj == ":"
                        and code[j : j + 2] != "::"
                        and code[max(0, j - 1) : j + 1] != "::"
                    ):
                        counter -= 1
                        if counter == 0:
                            colon_pos = j
                            break
                j += 1
            if colon_pos is None:
                i += 1
                continue
            k = colon_pos + 1
            k_in_str = None
            k_depth = 0
            stopped_at_close = False
            while k < n:
                ck = code[k]
                if k_in_str:
                    if ck == "\\":
                        k += 2
                        continue
                    if ck == k_in_str:
                        k_in_str = None
                    k += 1
                    continue
                if ck in ('"', "'", "`"):
                    k_in_str = ck
                    k += 1
                    continue
                if ck in _OPEN:
                    k_depth += 1
                elif ck in _CLOSE:
                    if k_depth == 0:
                        stopped_at_close = True
                        break
                    k_depth -= 1
                elif k_depth == 0 and ck in _BREAK_CHARS:
                    break
                k += 1
            else_end = k
            cond = code[cond_start:q_pos].strip()
            then = code[q_pos + 1 : colon_pos].strip()
            els = code[colon_pos + 1 : else_end].strip()
            if not cond or not then or not els:
                i += 1
                continue
            then = _resolve_all(then)
            els = _resolve_all(els)
            already_wrapped = break_is_open.get(depth, False) and stopped_at_close
            if already_wrapped:
                replacement = f"{then} if {cond} else {els}"
            else:
                replacement = f"({then} if {cond} else {els})"
            return code[:cond_start] + replacement + code[else_end:]
        i += 1
    return code


def _resolve_all(code):
    for _ in range(50):
        new_code = _fix_ternary_once(code)
        if new_code == code:
            return code
        code = new_code
    return code


def fix_ternary(s, n=10):
    for _ in range(n):
        new = _fix_ternary_once(s)
        if new == s:
            break
        s = new
    return s


if __name__ == "__main__":

    tests = [
        "        vector2Int += (a ? b : 0, a ? b : 0)",
        "x = a ? b : c;",
        "a ? b : c ? d : e",
        "foo(a ? b : c, d)",
        'name = cond ? "yes, really" : "no"',
        "        this.worldBlocks[j, num18] = ((noise2 > num19 && dirtPerlinNoise.GetNoise((float)j, (float)num18) < -0.4f) ? ((noise2 < num19 + 0.1f) ? 12 : 13) : 0);",
    ]
    for t in tests:
        print(repr(t))
        print(" ->", repr(fix_ternary(t)))
        print()
