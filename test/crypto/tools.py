from unittest import TestCase

from utils.common import random_bytes

from crypto.tools import bytes_add_padding, bytes_del_padding


class BytesPaddingTests(TestCase):

    def test_1(self):
        data = b""
        pad = bytes_add_padding(data, 0, 0)
        del_pad = bytes_del_padding(pad)
        self.assertEqual(data, del_pad)

    def test_2(self):
        data = random_bytes(1)
        pad = bytes_add_padding(data, 0, 0)
        del_pad = bytes_del_padding(pad)
        self.assertEqual(data, del_pad)

    def test_3(self):
        data = random_bytes(0)
        pad = bytes_add_padding(data, 1, 1)
        del_pad = bytes_del_padding(pad)
        self.assertEqual(data, del_pad)

    def test_4(self):
        data = random_bytes(100)
        pad = bytes_add_padding(data, 255, 255)
        del_pad = bytes_del_padding(pad)
        self.assertEqual(data, del_pad)

    def test_5(self):
        self.assertRaises(AssertionError, bytes_add_padding, b"", 256, 0)
        self.assertRaises(AssertionError, bytes_add_padding, b"", 0, 256)
