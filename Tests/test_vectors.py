from unittest import TestCase

from vectors import Vector


# noinspection PyTypeChecker
class TestVector(TestCase):
    def test_init(self):
        v1 = Vector(-3, 3)
        v2 = Vector(-3.2, 3.8)
        v3 = Vector((3, 6))
        self.assertEqual(v1, v2)
        self.assertEqual(Vector(3, 6), v3)
        with self.assertRaises(ValueError):
            Vector(3)
            Vector(-2, " ")

    def test_repr(self):
        v1 = Vector(2, 3)
        self.assertEqual(repr(v1), "Vector(2, 3)")

    def test_add(self):
        v1 = Vector(2, 3)
        v2 = Vector(-2, 5)
        self.assertEqual(v1 + v2, Vector(0, 8))
        self.assertEqual(v2 + v1, Vector(0, 8))
        with self.assertRaises(TypeError):
            v1 + (1, " ")
            v1 + (1,)
            v1 + " "

    def test_neg(self):
        v1 = Vector(2, 3)
        self.assertEqual(-v1, Vector(-2, -3))

    def test_sub(self):
        v1 = Vector(2, 3)
        v2 = Vector(-4, 0)
        self.assertEqual(v1 - v2, Vector(6, 3))
        self.assertEqual(v2 - v1, Vector(-6, -3))
        with self.assertRaises(TypeError):
            v1 - (1, " ")
            v1 - (1,)
            v1 + " "

    def test_mul(self):
        v1 = Vector(2, 3)
        v2 = Vector(-4, 0)
        self.assertEqual(v1 * 2, 2 * v1)
        self.assertEqual(v2 * 2, 2 * v2)
        self.assertEqual(v1 * 2.5, Vector(5, 7))
