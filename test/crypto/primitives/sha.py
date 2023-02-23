from unittest import TestCase

from utils.common import random_bytes

import crypto.primitives as p


class Sha3512RfcTests(TestCase):

   def test_0(self):
      data = b'abc'
      answer = bytes.fromhex('b751850b1a57168a 5693cd924b6b096e 08f621827444f70d 884f5d0240d2712e 10e116e9192af3c9 1a7ec57647e39340 57340b4cf408d5a5 6592f8274eec53f0')
      instance = p.Hash512SHA3()
      self.assertEqual(instance.process(data), answer)

   def test_1(self):
      data = b''
      answer = bytes.fromhex('a69f73cca23a9ac5 c8b567dc185a756e 97c982164fe25859 e0d1dcc1475c80a6 15b2123af1f5f94c 11e3e9402c3ac558 f500199d95b6d3e3 01758586281dcd26')
      instance = p.Hash512SHA3()
      self.assertEqual(instance.process(data), answer)

   def test_2(self):
      data = b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu'
      answer = bytes.fromhex('afebb2ef542e6579 c50cad06d2e578f9 f8dd6881d7dc824d 26360feebf18a4fa 73e3261122948efc fd492e74e82e2189 ed0fb440d187f382 270cb455f21dd185')
      instance = p.Hash512SHA3()
      self.assertEqual(instance.process(data), answer)
