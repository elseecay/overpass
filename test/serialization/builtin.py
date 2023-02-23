from unittest import TestCase

from serialization.base import *
from serialization.driver import *


def check_serdes(testcase, value):
    s = serialize(value)
    d = deserialize(s)
    testcase.assertEqual(d, value)


class BuiltinTests(TestCase):

    def test_0(self):
        check_serdes(self, None)

    def test_1(self):
        check_serdes(self, 1)

    def test_2(self):
        check_serdes(self, 1.0)

    def test_3(self):
        check_serdes(self, False)

    def test_4(self):
        check_serdes(self, "xxx")

    def test_5(self):
        check_serdes(self, b"xxx")

    def test_6(self):
        check_serdes(self, [1, 2])

    def test_7(self):
        check_serdes(self, {1: 2, 3: 4})

    def test_8(self):
        check_serdes(self, [b"xxx", b"yyy"])

    def test_9(self):
        check_serdes(self, [[1, 2], [3, 4]])

    def test_10(self):
        check_serdes(self, {1: b"xxx", 2: b"yyy"})

    def test_11(self):
        check_serdes(self, (1,))
        check_serdes(self, (1, 2))
        check_serdes(self, (1, 2, 3))

    def test_12(self):
        check_serdes(self, ({1: 2}, {b"3": "4"}))

    def test_13(self):
        check_serdes(self, bytearray([100, 100, 100]))

    def test_14(self):
        check_serdes(self, frozenset([1, 2, 3]))

    def test_15(self):
        check_serdes(self, ...)

    def test_16(self):
        check_serdes(self, {1, 2, 3})

    def test_17(self):
        check_serdes(self, range(1, 100, 4))