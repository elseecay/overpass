from unittest import TestCase

from utils.common import random_bytes

import crypto.primitives as p


def check_cipher(testcase, encryptor, data_size=1024):
    data = random_bytes(data_size)
    data_crypted = encryptor.process(data)
    decryptor = encryptor.opposite_instance()
    decryptor.key = encryptor.key
    data_decrypted = decryptor.process(data_crypted)
    testcase.assertEqual(data_decrypted, data)


class ChaCha20RfcTests(TestCase):

    def test_0(self):
        nonce = bytes.fromhex('00' * 16)
        key = bytes.fromhex('00' * 32)
        plain_text = bytes.fromhex('00' * 64)
        cipher_text = '76 b8 e0 ad a0 f1 3d 90 40 5d 6a e5 53 86 bd 28'
        cipher_text += 'bd d2 19 b8 a0 8d ed 1a a8 36 ef cc 8b 77 0d c7'
        cipher_text += 'da 41 59 7c 51 57 48 8d 77 24 e0 3f b8 d8 4a 37'
        cipher_text += '6a 43 b8 f4 15 18 a1 1c c3 87 b6 69 b2 ee 65 86'
        cipher_text = bytes.fromhex(cipher_text)
        encryptor = p.Enc256CHACHA(iv=nonce, key=key)
        decryptor = encryptor.opposite_instance()
        self.assertEqual(encryptor.process(plain_text), cipher_text)
        self.assertEqual(decryptor.process(cipher_text), plain_text)


class ChaCha20Tests(TestCase):

    def test_1(self):
      cipher = p.Enc256CHACHA(iv=b"1" * 16, key=b"1" * 32)
      check_cipher(self, cipher, 1024)

    def test_2(self):
      cipher = p.Enc256CHACHA(iv=b"2" * 16, key=b"2" * 32)
      check_cipher(self, cipher, 1024 * 128)
      check_cipher(self, cipher, 1024 * 256)
      check_cipher(self, cipher, 1024 * 512)
      check_cipher(self, cipher, 1024 * 1024)

    def test_3(self):
      cipher = p.Enc256CHACHA(iv=b"3" * 16, key=b"3" * 32)
      check_cipher(self, cipher, 1)
      check_cipher(self, cipher, 2)
      check_cipher(self, cipher, 13)
      check_cipher(self, cipher, 79)
