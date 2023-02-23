from unittest import TestCase

from utils.common import random_bytes

import crypto.primitives as p
from crypto.mixer import KeyHasher, Hasher


def check_key_hasher(testcase, key_hasher, data_size=1024):
    data = random_bytes(data_size)
    keys = key_hasher.process(data)
    for k, ksize in zip(keys, key_hasher.key_sizes):
        testcase.assertEqual(len(k), ksize)
    s = set(keys)
    testcase.assertEqual(len(keys), len(key_hasher.elements))
    testcase.assertEqual(len(s), len(keys))


def check_key_hasher_v2(testcase, *hashes, data_size=1024):
    data = random_bytes(data_size)
    data_from_hashes = data
    keys_from_hashes = []
    for h in hashes:
        data_from_hashes = h.process(data_from_hashes)
        keys_from_hashes.append(data_from_hashes)
    key_hasher = KeyHasher(*hashes)
    keys_from_key_hasher = key_hasher.process(data)
    testcase.assertEqual(keys_from_key_hasher, keys_from_hashes)


class CryptoKeyHasherTests(TestCase):

    def test_0(self):
        data = b'abc'
        answer = bytes.fromhex('b751850b1a57168a 5693cd924b6b096e 08f621827444f70d 884f5d0240d2712e 10e116e9192af3c9 1a7ec57647e39340 57340b4cf408d5a5 6592f8274eec53f0')
        hash = p.Hash512SHA3()
        key_hasher = KeyHasher(hash)
        keys = key_hasher.process(data)
        self.assertEqual(keys[0], answer)
        self.assertEqual(len(keys), 1)

    def test_1(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        key_hasher = KeyHasher(hash, hash2)
        check_key_hasher(self, key_hasher)

    def test_2(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        key_hasher = KeyHasher(hash, hash2)
        check_key_hasher(self, key_hasher, data_size=999999)

    def test_3(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        key_hasher = Hasher(hash, hash2)
        key_hasher2 = Hasher(hash2, hash)
        self.assertNotEqual(key_hasher.process(b"1"), key_hasher2.process(b"1"))

    def test_4(self):
        hash = p.Hash512SHA3()
        hash2 = p.Hash256SHA3()
        check_key_hasher_v2(self, hash, hash2)

    def test_5(self):
        hash1 = Hasher(p.Hash512SHA3(), iterations=10)
        hash2 = Hasher(p.VarHashShake256(digest_size=40), p.Hash224SHA3(), iterations=5)
        check_key_hasher_v2(self, hash1, hash2)
