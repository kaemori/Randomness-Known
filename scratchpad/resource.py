from dataclasses import dataclass


@dataclass
class Quaternion:
    identity = [0, 0, 0]

    @staticmethod
    def Euler(x, y, z):
        return z


print(Quaternion.identity)
