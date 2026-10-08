import struct


class UnityRandom:
    def __init__(self, s0, s1, s2, s3):
        self.s0 = s0 & 0xFFFFFFFF
        self.s1 = s1 & 0xFFFFFFFF
        self.s2 = s2 & 0xFFFFFFFF
        self.s3 = s3 & 0xFFFFFFFF

    def _next(self):
        t = self.s3
        self.s0 = self.s1
        self.s1 = self.s2
        self.s2 = self.s3
        # print(self._state)
        t ^= (t << 11) & 0xFFFFFFFF
        t ^= t >> 8
        t ^= self.s0
        t ^= self.s0 >> 19
        self.s3 = t
        return self.s0

    @property
    def _state(self):
        return (self.s0, self.s1, self.s2, self.s3)

    @property
    def _state_unitylike(self):
        return {f"s{i}": st for i, st in zip(range(4), self._state)}

    def value(self):
        return (self._next() & 0x7FFFFF) / float(0x800000)

    def range_float(self, min_val, max_val):
        return min_val + self.value() * (max_val - min_val)

    def range_int(self, min_inclusive, max_exclusive):
        span = max_exclusive - min_inclusive
        if span == 0:
            return min_inclusive
        return min_inclusive + int(self.value() * span)


startstate = {"s0": 3283155317, "s1": 524985772, "s2": 1247495602, "s3": 859501417}
startstate = list(startstate.values())


gamerand = UnityRandom(*startstate)
for i in range(10):
    print(gamerand._state_unitylike)
    gamerand._next()


# ({'s0': 3283155317, 's1': 524985772, 's2': 1247495602, 's3': 859501417})
# ({'s0': 524985772, 's1': 1247495602, 's2': 859501417, 's3': 1996873514})
# ({'s0': 1247495602, 's1': 859501417, 's2': 1996873514, 's3': 1026061219})
# ({'s0': 859501417, 's1': 1996873514, 's2': 1026061219, 's3': 2916013921})
# ({'s0': 1996873514, 's1': 1026061219, 's2': 2916013921, 's3': 1233901578})
# ({'s0': 1026061219, 's1': 2916013921, 's2': 1233901578, 's3': 271491742})
# ({'s0': 2916013921, 's1': 1233901578, 's2': 271491742, 's3': 1860533843})
# ({'s0': 1233901578, 's1': 271491742, 's2': 1860533843, 's3': 3041646897})
# ({'s0': 271491742, 's1': 1860533843, 's2': 3041646897, 's3': 2719419418})
# ({'s0': 1860533843, 's1': 3041646897, 's2': 2719419418, 's3': 3343413396})
# ({'s0': 3041646897, 's1': 2719419418, 's2': 3343413396, 's3': 2182781384})
# ({'s0': 2719419418, 's1': 3343413396, 's2': 2182781384, 's3': 1769167595})
# ({'s0': 3343413396, 's1': 2182781384, 's2': 1769167595, 's3': 1931410435})
# ({'s0': 2182781384, 's1': 1769167595, 's2': 1931410435, 's3': 4149669412})
# ({'s0': 1769167595, 's1': 1931410435, 's2': 4149669412, 's3': 2715090399})
# ({'s0': 1931410435, 's1': 4149669412, 's2': 2715090399, 's3': 1384337164})
# ({'s0': 4149669412, 's1': 2715090399, 's2': 1384337164, 's3': 3606667195})
