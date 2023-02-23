from unittest import TestCase

from utils.common import random_bytes

import crypto.primitives as p


class Shake128RfcTests(TestCase):

   def test_0(self):
       data = 'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'.encode("utf-8")
       answer = bytes.fromhex('1a96182b50fb8c7e74e0a707788f55e98209b8d91fade8f32f8dd5cff7bf21f5')
       instance = p.VarHashShake128(digest_size=32)
       self.assertEqual(instance.process(data), answer)


class Shake256RfcTests(TestCase):

   def test_0(self):
       data = 'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'.encode("utf-8")
       answer = bytes.fromhex('4d8c2dd2435a0128eefbb8c36f6f87133a7911e18d979ee1ae6be5d4fd2e332940d8688a4e6a59aa8060f1f9bc996c05aca3c696a8b66279dc672c740bb224ec')
       instance = p.VarHashShake256(digest_size=64)
       self.assertEqual(instance.process(data), answer)
