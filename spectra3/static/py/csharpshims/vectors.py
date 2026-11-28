import math


class Vector2:
    __slots__ = ("x", "y")

    def __init__(self, x, y=None):
        self.x, self.y = (x[0], x[1]) if y is None else (x, y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, index):
        return (self.x, self.y)[index]

    def __add__(self, other):
        return Vector2(self.x + other[0], self.y + other[1])

    __radd__ = __add__

    def __sub__(self, other):
        return Vector2(self.x - other[0], self.y - other[1])

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def magnitude(self):
        return math.hypot(self.x, self.y)

    @property
    def normalized(self):
        length = self.magnitude()
        return Vector2(self.x / length, self.y / length) if length else Vector2(0, 0)

    @staticmethod
    def Distance(first, second):
        return (first - second).magnitude()

    @staticmethod
    def Lerp(first, second, t):
        return first + (second - first) * t

    @staticmethod
    def SignedAngle(first, second):
        cross = first.x * second.y - first.y * second.x
        dot = first.x * second.x + first.y * second.y
        return math.degrees(math.atan2(cross, dot))


Vector2.zero = Vector2(0, 0)
Vector2.one = Vector2(1, 1)
Vector2.up = Vector2(0, 1)
Vector2.down = Vector2(0, -1)
Vector2.left = Vector2(-1, 0)
Vector2.right = Vector2(1, 0)


class Vector3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y=None, z=None):
        self.x, self.y, self.z = (x[0], x[1], x[2]) if y is None else (x, y, z)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, index):
        return (self.x, self.y, self.z)[index]

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar):
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)
