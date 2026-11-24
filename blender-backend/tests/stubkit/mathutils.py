"""Minimal mathutils stand-in: only Vector, as used by generated scripts."""

import math


class Vector:
    def __init__(self, seq=(0.0, 0.0, 0.0)):
        self._v = tuple(float(x) for x in seq)

    def __iter__(self):
        return iter(self._v)

    def __getitem__(self, i):
        return self._v[i]

    def __len__(self):
        return len(self._v)

    def __repr__(self):
        return f"Vector({self._v})"

    def to_track_quat(self, *args, **kwargs):
        return self

    def to_euler(self):
        return (0.0, 0.0, 0.0)

    def __sub__(self, other):
        return Vector(a - b for a, b in zip(self._v, other))

    def __add__(self, other):
        return Vector(a + b for a, b in zip(self._v, other))

    @property
    def length(self):
        return math.sqrt(sum(x * x for x in self._v))


class Matrix:
    def __init__(self, *args, **kwargs):
        pass


class Euler:
    def __init__(self, seq=(0.0, 0.0, 0.0)):
        self._v = tuple(seq)


def noise(*args, **kwargs):
    return 0.0
