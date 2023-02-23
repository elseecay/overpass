from unittest import TestCase

from utils.common import random_bytes

import crypto.primitives as p
from crypto.mixer import Hasher


def check_hasher(testcase, hasher, data_size=1024):
    data = random_bytes(data_size)
    data_hashed = hasher.process(data)
    testcase.assertEqual(len(data_hashed), hasher.digest_size)


def check_hasher_v2(testcase, *hashes, iterations=1, data_size=1024):
    data = random_bytes(data_size)
    data_from_hashes = data
    for _ in range(iterations):
        for h in hashes:
            data_from_hashes = h.process(data_from_hashes)
    hasher = Hasher(*hashes, iterations=iterations)
    data_from_hasher = hasher.process(data)
    testcase.assertEqual(data_from_hasher, data_from_hashes)


class CryptoHasherTests(TestCase):

    def test_0(self):
        data = b'abc'
        answer = bytes.fromhex('b751850b1a57168a 5693cd924b6b096e 08f621827444f70d 884f5d0240d2712e 10e116e9192af3c9 1a7ec57647e39340 57340b4cf408d5a5 6592f8274eec53f0')
        hash = p.Hash512SHA3()
        hasher = Hasher(hash, iterations=1)
        hashed = hasher.process(data)
        self.assertEqual(hashed, answer)

    def test_1(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=1)
        check_hasher(self, hasher)

    def test_2(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=2)
        check_hasher(self, hasher)

    def test_3(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=2)
        check_hasher(self, hasher, data_size=999999)

    def test_4(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=1)
        hasher2 = Hasher(hash, hash2, iterations=2)
        self.assertNotEqual(hasher.process(b"1"), hasher2.process(b"1"))

    def test_5(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=1)
        hasher2 = Hasher(hash2, hash, iterations=1)
        self.assertNotEqual(hasher.process(b"1"), hasher2.process(b"1"))

    def test_6(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash, hash2, iterations=1)
        hasher = Hasher(hasher, hasher, iterations=5)
        check_hasher(self, hasher)

    def test_7(self):
        hash1 = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        hasher = Hasher(hash1, hash2)
        data = b"x" * 100
        data_from_hashes = hash2.process(hash1.process(data))
        data_from_hasher = hasher.process(data)
        self.assertEqual(data_from_hasher, data_from_hashes)

    def test_8(self):
        hash1 = p.VarHashShake128(digest_size=50)
        hash2 = p.Hash224SHA3()
        check_hasher_v2(self, hash1, hash2, iterations=10)

    def test_9(self):
        hash1 = p.VarHashShake128(digest_size=50)
        hash2 = p.Hash224SHA3()
        hash3 = p.Hash256SHA3()
        check_hasher_v2(self, Hasher(hash1, hash2, iterations=2), hash3, iterations=10)
