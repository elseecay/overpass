from unittest import TestCase

from utils.encoding import *



class EncodingTests(TestCase):

    def test_1(self):
        self.assertEqual(encode_utf8("123"), b"123")

    def test_2(self):
        self.assertEqual(decode_utf8(b"123"), "123")

    def test_3(self):
        self.assertEqual(encode_base64(b"hello"), "aGVsbG8=")

    def test_4(self):
        self.assertEqual(decode_base64("aGVsbG8="), b"hello")

    def test_5(self):
        data = "eyJhIjogMSwgImIiOiBbMSwgMiwgM119"
        expected = {"a": 1, "b": [1, 2, 3]}
        self.assertEqual(decode_json_base64(data), expected)