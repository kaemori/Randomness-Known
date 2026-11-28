"""
Fast Python port of Unity's AnimationCurve.Evaluate (clamp wrap mode).

Unity evaluates cubic Hermite segments between consecutive keyframes:
    t = (time - k0.time) / (k1.time - k0.time)   # normalized 0..1
    dt = k1.time - k0.time
    m0 = k0.outTangent * dt
    m1 = k1.inTangent * dt
    value = h00(t)*k0.value + h10(t)*m0 + h01(t)*k1.value + h11(t)*m1

Rather than recompute the Hermite basis functions every call, we expand
h00/h10/h01/h11 and bake everything down to a plain cubic
    value = a*t^3 + b*t^2 + c*t + d
per segment at construction time. Evaluate() then does a binary search
for the segment and a 3-multiply polynomial eval -- fast enough for
millions of calls.

Outside the curve's time range, value clamps to the first/last keyframe's
value (matching Unity's default WrapMode.ClampForever behavior).
"""

from bisect import bisect_right

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


class Keyframe:
    __slots__ = ("time", "value", "in_tangent", "out_tangent")

    def __init__(self, time, value, in_tangent, out_tangent):
        self.time = float(time)
        self.value = float(value)
        self.in_tangent = float(in_tangent)
        self.out_tangent = float(out_tangent)


class AnimationCurve:
    """
    Usage:
        curve = AnimationCurve([
            Keyframe(0, 0.04369995, -0.05734595, -0.05734595),
            Keyframe(0.2, 0.03223076, -0.02508016, -0.02508016),
            Keyframe(0.5213115, 0.03974618, -0.003112201, -0.003112201),
            Keyframe(1, 0.0437015, 0.05906005, 0.05906005),
        ])
        curve.Evaluate(0.37)

    Or directly from raw tuples:
        curve = AnimationCurve.from_tuples([
            (0, 0.04369995, -0.05734595, -0.05734595),
            ...
        ])
    """

    __slots__ = (
        "_times",
        "_coeffs",
        "_first_value",
        "_last_value",
        "_times_np",
        "_coeffs_np",
    )

    def __init__(self, keyframes):
        keyframes = sorted(keyframes, key=lambda k: k.time)
        if len(keyframes) < 1:
            raise ValueError("AnimationCurve needs at least one keyframe")

        self._times = [k.time for k in keyframes]
        self._first_value = keyframes[0].value
        self._last_value = keyframes[-1].value

        coeffs = []
        for i in range(len(keyframes) - 1):
            k0 = keyframes[i]
            k1 = keyframes[i + 1]
            dt = k1.time - k0.time
            if dt <= 0.0:
                coeffs.append((0.0, 0.0, 0.0, k0.value))
                continue

            m0 = k0.out_tangent * dt
            m1 = k1.in_tangent * dt
            p0 = k0.value
            p1 = k1.value

            a = 2 * p0 + m0 - 2 * p1 + m1
            b = -3 * p0 - 2 * m0 + 3 * p1 - m1
            c = m0
            d = p0
            coeffs.append((a, b, c, d))

        self._coeffs = coeffs

        if _HAS_NUMPY:
            self._times_np = np.array(self._times, dtype=np.float64)
            self._coeffs_np = (
                np.array(coeffs, dtype=np.float64) if coeffs else np.zeros((0, 4))
            )
        else:
            self._times_np = None
            self._coeffs_np = None

    @classmethod
    def from_tuples(cls, rows):
        return cls([Keyframe(*r) for r in rows])

    def Evaluate(self, time):
        if _HAS_NUMPY and (
            isinstance(time, np.ndarray)
            or (hasattr(time, "__len__") or hasattr(time, "__iter__"))
        ):
            return self._evaluate_array(np.asarray(time, dtype=np.float64))

        return self._evaluate_scalar(float(time))

    def _evaluate_scalar(self, time):
        times = self._times
        n = len(times)

        if time <= times[0]:
            return self._first_value
        if time >= times[-1]:
            return self._last_value
        if n == 1:
            return self._first_value

        idx = bisect_right(times, time) - 1
        if idx >= n - 1:
            idx = n - 2

        t0 = times[idx]
        t1 = times[idx + 1]
        t = (time - t0) / (t1 - t0)

        a, b, c, d = self._coeffs[idx]
        return ((a * t + b) * t + c) * t + d

    def _evaluate_array(self, time):
        if not _HAS_NUMPY:
            raise RuntimeError("NumPy is required for array input")

        times_np = self._times_np
        n = len(times_np)

        if n == 1:
            return np.full(time.shape, self._first_value, dtype=np.float64)

        clamped = np.clip(time, times_np[0], times_np[-1])

        idx = np.searchsorted(times_np, clamped, side="right") - 1
        idx = np.clip(idx, 0, n - 2)

        t0 = times_np[idx]
        t1 = times_np[idx + 1]
        t = (clamped - t0) / (t1 - t0)

        coeffs = self._coeffs_np[idx]
        a = coeffs[..., 0]
        b = coeffs[..., 1]
        c = coeffs[..., 2]
        d = coeffs[..., 3]

        result = ((a * t + b) * t + c) * t + d

        result = np.where(time <= times_np[0], self._first_value, result)
        result = np.where(time >= times_np[-1], self._last_value, result)
        return result

    __call__ = Evaluate
