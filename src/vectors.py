"""
Supporting module for vector and coordinate calculations.

version: 1.0
author: ZCR
"""

import numbers
from collections.abc import Iterable
from enum import IntEnum
from typing import overload

__all__ = ['Cell', 'Vector', 'vec_like', 'DIR_VECS', 'DIR_ENUMS']


class Cell(IntEnum):
    EMPTY = 0
    GO_RIGHT = 1
    GO_UP = 2
    GO_LEFT = 3
    GO_DOWN = 4
    END_P = 5


class Vector(tuple):
    """Two-dimensional vector, implemented add & sub operations, their result are all Vectors."""

    @overload
    def __new__(cls, x: numbers.Real, y: numbers.Real):
        pass

    @overload
    def __new__(cls, seq: Iterable):
        pass

    def __new__(cls, *args):
        if isinstance(args[0], Iterable):
            return tuple.__new__(cls, args[0])
        elif isinstance(args[0], numbers.Real) and len(args) == 2 and isinstance(args[1], numbers.Real):
            return tuple.__new__(cls, (int(args[0]), int(args[1])))
        else:
            raise ValueError("argument must be iterable or two numbers")

    def __repr__(self):
        return f"Vector({self[0]}, {self[1]})"

    def __add__(self, other):
        try:
            return Vector(self[0] + other[0], self[1] + other[1])
        except TypeError:
            raise TypeError(f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'")
        except IndexError:
            raise TypeError("other must be a vector_like object of length 2")

    def __radd__(self, other):
        try:
            return Vector(self[0] + other[0], self[1] + other[1])
        except TypeError:
            raise TypeError(f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'")
        except IndexError:
            raise TypeError("other must be a vector_like object of length 2")

    def __neg__(self):
        return Vector(-self[0], -self[1])

    def __sub__(self, other):
        try:
            return Vector(self[0] - other[0], self[1] - other[1])
        except TypeError:
            raise TypeError(f"unsupported operand type(s) for -: '{type(self).__name__}' and '{type(other).__name__}'")
        except IndexError:
            raise TypeError("other must be a vector_like object of length 2")

    def __rsub__(self, other):
        try:
            return Vector(other[0] - self[0], other[1] - self[1])
        except TypeError:
            raise TypeError(f"unsupported operand type(s) for -: '{type(self).__name__}' and '{type(other).__name__}'")
        except IndexError:
            raise TypeError("other must be a vector_like object of length 2")

    def __mul__(self, other: numbers.Real):
        if not isinstance(other, numbers.Real):
            raise ValueError("argument must be real number")
        return Vector(int(self[0] * other), int(self[1] * other))

    def __rmul__(self, other: numbers.Real):
        if not isinstance(other, numbers.Real):
            raise ValueError("argument must be real number")
        return Vector(int(self[0] * other), int(self[1] * other))


vec_like = tuple[int, int] | Vector

DIR_VECS = {Cell.GO_LEFT: Vector(-1, 0),
            Cell.GO_RIGHT: Vector(1, 0),
            Cell.GO_UP: Vector(0, -1),
            Cell.GO_DOWN: Vector(0, 1)}
DIR_ENUMS = {vecs: enums for enums, vecs in DIR_VECS.items()}

if __name__ == '__main__':
    pass
