# recycled from old projects lol

import math


class Vector2:
    zero = None
    one = None
    up = None
    down = None
    left = None
    right = None

    def __init__(self, x: int, y: int):
        self.x, self.y = x, y

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"

    def __iter__(self):
        yield self.x
        yield self.y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float):
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float):
        return Vector2(self.x / scalar, self.y / scalar)

    def __floordiv__(self, scalar: int):
        return Vector2(self.x // scalar, self.y // scalar)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        else:
            raise IndexError("Index out of range for Vector2")

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def magnitude(self):
        return math.sqrt((self.x * self.x + self.y * self.y))

    def normalize(self):
        mag = self.magnitude()
        return Vector2(self.x / mag, self.y / mag) if mag != 0 else Vector2(0, 0)

    def copy(self):
        return Vector2(self.x, self.y)

    @staticmethod
    def Distance(first, second):
        return (first - second).magnitude()


Vector2.zero = Vector2(0, 0)
Vector2.one = Vector2(1, 1)
Vector2.up = Vector2(0, 1)
Vector2.down = Vector2(0, -1)
Vector2.left = Vector2(-1, 0)
Vector2.right = Vector2(1, 0)


class Rot:
    def __init__(self, pitch: int, yaw: int):
        self.pitch, self.yaw = pitch, yaw

    def __repr__(self):
        return f"Rot({self.pitch}, {self.yaw})"

    def __iter__(self):
        yield self.pitch
        yield self.yaw

    def __add__(self, other):
        return Rot(self.pitch + other.pitch, self.yaw + other.yaw)

    def __sub__(self, other):
        return Rot(self.pitch - other.pitch, self.yaw - other.yaw)

    def __mul__(self, scalar: float):
        return Rot(self.pitch * scalar, self.yaw * scalar)

    def __truediv__(self, scalar: float):
        return Rot(self.pitch / scalar, self.yaw / scalar)

    def __floordiv__(self, scalar: int):
        return Rot(self.pitch // scalar, self.yaw // scalar)

    def __neg__(self):
        return Rot(-self.pitch, -self.yaw)

    def __eq__(self, other):
        return self.pitch == other.pitch and self.yaw == other.yaw

    def __getitem__(self, index):
        if index == 0:
            return self.pitch
        elif index == 1:
            return self.yaw
        else:
            raise IndexError("Index out of range for Rot")

    def dot(self, other):
        return self.pitch * other.pitch + self.yaw * other.yaw

    def magnitude(self):
        return math.sqrt((self.pitch * self.pitch + self.yaw * self.yaw))

    def normalize(self):
        mag = self.magnitude()
        return Rot(self.pitch / mag, self.yaw / mag) if mag != 0 else Rot(0, 0)

    def copy(self):
        return Rot(self.pitch, self.yaw)


class Vector3:
    def __init__(self, x: float | list, y: float = None, z: float = None):
        if y is None and z is None:
            self.x, self.y, self.z = x
        else:
            self.x, self.y, self.z = x, y, z

    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float):
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __floordiv__(self, scalar: int):
        return Vector3(self.x // scalar, self.y // scalar, self.z // scalar)

    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self.x, self.y, self.z][index]
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z
        else:
            raise IndexError("Index out of range for Vector3")

    def __setitem__(self, index, value):
        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        elif index == 2:
            self.z = value
        else:
            raise IndexError("Index out of range for Vector3")

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def magnitude(self):
        return math.sqrt((self.x * self.x + self.y * self.y + self.z * self.z))

    def normalize(self):
        mag = self.magnitude()
        return (
            Vector3(self.x / mag, self.y / mag, self.z / mag)
            if mag != 0
            else Vector3(0, 0, 0)
        )

    def copy(self):
        return Vector3(self.x, self.y, self.z)


def zero3():
    return Vector3(0, 0, 0)


def zero2():
    return Vector2(0, 0)
