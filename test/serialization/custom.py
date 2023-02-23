from unittest import TestCase

from dataclasses import dataclass

from serialization.base import *
from serialization.driver import *
from serialization.utils import *


@dataclass
class MyClass:
    b: bool = False
    i: int = 0
    f: float = 0.0
    s: str = ""
    bt: bytes = b""
    o: object = None

    def func(self):
        return self.i + 5


register_trivial_attrib_serializer(MyClass, 5000)


def check_serdes(testcase, value):
    s = serialize(value)
    d = deserialize(s)
    testcase.assertEqual(d, value)


class CustomTests(TestCase):

    def test_1(self):
        check_serdes(self, MyClass(b=True))

    def test_2(self):
        check_serdes(self, MyClass(i=1))

    def test_3(self):
        check_serdes(self, MyClass(f=1.1))

    def test_4(self):
        check_serdes(self, MyClass(s="123"))

    def test_5(self):
        check_serdes(self, MyClass(bt=b"123"))

    def test_6(self):
        check_serdes(self, MyClass(o=MyClass(i=1, f=2.0, s="555", bt=b"444")))

    def test_7(self):
        obj = MyClass(i=1)
        s = serialize(obj)
        d = deserialize(s)
        self.assertEqual(d.func(), 6)