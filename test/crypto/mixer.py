from unittest import TestCase

from functools import reduce

from utils.common import random_bytes

import crypto.primitives as p
from crypto.mixer import Mixer


def check_mixer(testcase, mixer, data_size=1024):
    data = random_bytes(data_size)
    keys = [random_bytes(size) for size in mixer.key_sizes]
    mixer.set_keys(*keys)
    iv = mixer.iv_set_random()
    data_crypted = mixer.process(data)
    mixer = mixer.opposite_instance()
    mixer.iv_set(iv)
    data_decrypted = mixer.process(data_crypted)
    testcase.assertEqual(data, data_decrypted)
    mixer = mixer.opposite_instance()
    mixer.iv_set(iv, iv_order_reverse=False)
    data_crypted2 = mixer.process(data)
    testcase.assertEqual(data_crypted2, data_crypted)


def check_mixer_v2(testcase, *ciphers, data_size=1024):
    ivs = [random_bytes(cipher.IV_SIZE) for cipher in ciphers]
    keys = [random_bytes(cipher.KEY_SIZE) for cipher in ciphers]
    for cipher, key, iv in zip(ciphers, keys, ivs):
        cipher.key = key
        cipher.iv = iv
    mixer = Mixer(*ciphers, keys=keys)
    mixer.iv_set(ivs, iv_order_reverse=False)
    data = random_bytes(data_size)
    data_from_ciphers = reduce(lambda accum, cipher: cipher.process(accum), ciphers, data)
    data_from_mixer = mixer.process(data)
    testcase.assertEqual(data_from_ciphers, data_from_mixer)


class CryptoMixerTests(TestCase):

    def test_1(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        mixer = Mixer(cipher, keys=[b"1" * 32])
        check_mixer(self, mixer)

    def test_2(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        cipher2 = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        mixer = Mixer(cipher, cipher2, keys=[b"1" * 32, b"2" * 32])
        check_mixer(self, mixer)

    def test_3(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        cipher2 = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        mixer = Mixer(cipher, cipher2, keys=[b"1" * 32, b"2" * 32])
        check_mixer(self, mixer, data_size=999999)

    def test_4(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        cipher2 = p.Enc256CAMELLIACTR(iv=b"2" * 16, key=b"2" * 32)
        cipher3 = p.Enc256CHACHA(iv=16 * b'1', key=32 * b'1')
        mixer = Mixer(cipher, cipher2, cipher3, keys=[b"1" * 32, b"2" * 32, b"3" * 32])
        check_mixer(self, mixer)

    def test_5(self):
        ivs = [b"A" * 16, b"B" * 16, b"C" * 16]
        keys = [b"1" * 32, b"2" * 32, b"3" * 32]
        cipher1 = p.Enc256AESCTR(iv=ivs[0], key=keys[0])
        cipher2 = p.Enc256CAMELLIACTR(iv=ivs[1], key=keys[1])
        cipher3 = p.Enc256CHACHA(iv=ivs[2], key=keys[2])
        mixer = Mixer(cipher1, cipher2, cipher3, keys=keys)
        mixer.iv_set(ivs, iv_order_reverse=False)
        data = b"D" * 100
        data_from_mixer = mixer.process(data)
        data_from_ciphers = cipher1.process(data)
        data_from_ciphers = cipher2.process(data_from_ciphers)
        data_from_ciphers = cipher3.process(data_from_ciphers)
        self.assertEqual(data_from_ciphers, data_from_mixer)
        opp_mixer = mixer.opposite_instance()
        opp_mixer.iv_set(ivs)
        self.assertEqual(data, opp_mixer.process(data_from_ciphers))

    def test_6(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        check_mixer_v2(self, cipher)

    def test_7(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        cipher2 = p.Enc256AESCTR(iv=b"2" * 16, key=b"2" * 32)
        check_mixer_v2(self, cipher, cipher2, data_size=99999)

    def test_deepcopy(self):
        cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
        mixer = Mixer(cipher, cipher)
        self.assertNotEqual(id(mixer.elements[0]), id(mixer.elements[1]))
