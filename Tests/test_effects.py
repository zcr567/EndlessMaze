from unittest import TestCase
from effects import *


class TestFuncs(TestCase):
    def test_trim(self):
        self.assertEqual(trim(0.5), 0.5)
        self.assertEqual(trim(1.0), 1)
        self.assertEqual(trim(0.7, -1, 0.5), 0.5)
        self.assertEqual(trim(0.2, 0.5, 0.7), 0.5)
        self.assertEqual(trim(0.1, 0.5, 0.5), 0.5)
        with self.assertRaises(ValueError):
            trim(0.2, 0.5, 0.3)


class TestInterpolationSubclass(TestCase):
    def test_Linear(self):
        i = Linear(10)
        i.update()
        self.assertEqual(i.get(), 0.1)
        i.set(0.25)
        self.assertEqual(i.get(), 0.25)
        for _ in range(8):
            i.update()
        self.assertEqual(i.get(), 1)
        i.switch()
        i.update()
        self.assertEqual(i.get(), 0.9)

    def test_Quad(self):
        self.fail()

    def test_DoubleQuad(self):
        self.fail()


class TestEffect(TestCase):
    def test_update(self):
        self.fail()
