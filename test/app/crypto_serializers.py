from unittest import TestCase

from utils.common import random_bytes

from serialization.base import serialize, deserialize

import crypto.primitives as p

from crypto.mixer import Mixer, KeyHasher, Hasher

import app.storage.crypto_serializers


def check_cipher(testcase, obj, data_size=1024):
    data = random_bytes(data_size)
    data_crypted = obj.process(data)
    s = serialize(obj)
    testcase.assertNotIn("key", s)
    d = deserialize(s)
    d.key = obj.key
    data_crypted_2 = d.process(data)
    testcase.assertEqual(data_crypted, data_crypted_2)


class SerializationCipherTests(TestCase):

    def test_0(self):
        cipher = p.Enc256CAMELLIACTR(iv=16 * b'1', key=32 * b'1')
        check_cipher(self, cipher)

    def test_1(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        check_cipher(self, cipher)

    def test_2(self):
        cipher = p.Enc256CHACHA(iv=b"1" * 16, key=b"1" * 32)
        check_cipher(self, cipher)


def mixer_set_key(mixer):
    keys = [random_bytes(size) for size in mixer.key_sizes]
    mixer.set_keys(*keys)


def check_mixer(testcase, mixer, data_size=1024):
    data = random_bytes(data_size)
    mixer_set_key(mixer)
    s = serialize(mixer)
    testcase.assertNotIn("key", s)
    testcase.assertNotIn("keys", s)
    data_crypted = mixer.process(data)
    d = deserialize(s)
    keys = [elem.key for elem in mixer.elements]
    d.set_keys(*keys)
    data_crypted_2 = d.process(data)
    testcase.assertEqual(data_crypted, data_crypted_2)


class SerializationMixerTests(TestCase):

    def test_1(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        mixer = Mixer(cipher)
        check_mixer(self, mixer)

    def test_2(self):
        cipher1 = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        cipher2 = p.Enc256CHACHA(iv=16 * b'1', key=32 * b'1')
        mixer = Mixer(cipher1, cipher2)
        check_mixer(self, mixer)

    def test_3(self):
        cipher1 = p.Enc256CHACHA(iv=16 * b'1', key=32 * b'1')
        cipher2 = p.Enc256AESCTR(iv=16 * b'1', key=32 * b'1')
        cipher3 = p.Enc256CAMELLIACTR(iv=16 * b'1', key=32 * b'1')
        mixer = Mixer(cipher1, cipher2, cipher3)
        check_mixer(self, mixer, 999999)


def check_key_hasher(testcase, key_hasher, data_size=1024):
    data = random_bytes(data_size)
    keys = key_hasher.process(data)
    s = serialize(key_hasher)
    d = deserialize(s)
    keys2 = d.process(data)
    testcase.assertEqual(keys, keys2)


class SerializationKeyHasherTests(TestCase):

    def test_1(self):
        h1 = p.Hash256SHA3()
        h2 = p.Hash512BLAKE2()
        h3 = p.VarHashShake256(digest_size=32)
        h4 = p.Hash256Scrypt(salt=random_bytes(16), n=2**14, r=8)
        key_hasher = KeyHasher(h1, h2, Hasher(h3, h4))
        check_key_hasher(self, key_hasher)


def check_hasher(testcase, hasher, data_size=1024):
    data = random_bytes(data_size)
    digest = hasher.process(data)
    s = serialize(hasher)
    d = deserialize(s)
    digest2 = d.process(data)
    testcase.assertEqual(digest, digest2)


class SerializationHasherTests(TestCase):

    def test_1(self):
        h1 = p.Hash256SHA3()
        h2 = p.Hash512BLAKE2()
        h3 = p.VarHashShake256(digest_size=32)
        hasher = Hasher(h1, h2, h3, Hasher(h2, h3))
        check_hasher(self, hasher)
