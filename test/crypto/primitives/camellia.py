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


class CamelliaCtrRfcTests(TestCase):

   def test_0(self):
      ctr = bytes.fromhex('00 FA AC 24 C1 58 5E F1 5A 43 D8 75 00 00 00 01')
      key = bytes.fromhex('F6 D6 6D 6B D5 2D 59 BB 07 96 36 58 79 EF F8 86 C6 6D D5 1A 5B 6A 99 74 4B 50 59 0C 87 A2 38 84')
      plain_text = bytes.fromhex('00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F')
      cipher_text = bytes.fromhex('D6 C3 03 92 24 6F 78 08 A8 3C 2B 22 A8 83 9E 45 E5 1C D4 8A 1C DF 40 6E BC 9C C2 D3 AB 83 41 08')
      encryptor = p.Enc256CAMELLIACTR(iv=ctr, key=key)
      decryptor = encryptor.opposite_instance()
      self.assertEqual(encryptor.process(plain_text), cipher_text)
      self.assertEqual(decryptor.process(cipher_text), plain_text)

   def test_1(self):
      ctr = bytes.fromhex('00 00 00 60 DB 56 72 C9 7A A8 F0 B2 00 00 00 01')
      key = bytes.fromhex('77 6B EF F2 85 1D B0 6F 4C 8A 05 42 C8 69 6F 6C 6A 81 AF 1E EC 96 B4 D3 7F C1 D6 89 E6 C1 C1 04')
      plain_text = bytes.fromhex('53 69 6E 67 6C 65 20 62 6C 6F 63 6B 20 6D 73 67')
      cipher_text = bytes.fromhex('34 01 F9 C8 24 7E FF CE BD 69 94 71 4C 1B BB 11')
      encryptor = p.Enc256CAMELLIACTR(iv=ctr, key=key)
      decryptor = encryptor.opposite_instance()
      self.assertEqual(encryptor.process(plain_text), cipher_text)
      self.assertEqual(decryptor.process(cipher_text), plain_text)


class CamelliaCtrTests(TestCase):

   def test_1(self):
      cipher = p.Enc256CAMELLIACTR(iv=b"1" * 16, key=b"1" * 32)
      check_cipher(self, cipher, 4096)

   def test_2(self):
      cipher = p.Enc256CAMELLIACTR(iv=b"2" * 16, key=b"2" * 32)
      check_cipher(self, cipher, 1024 * 128)
      check_cipher(self, cipher, 1024 * 256)
      check_cipher(self, cipher, 1024 * 512)
      check_cipher(self, cipher, 1024 * 1024)

   def test_3(self):
      cipher = p.Enc256CAMELLIACTR(iv=b"3" * 16, key=b"3" * 32)
      check_cipher(self, cipher, 1)
      check_cipher(self, cipher, 2)
      check_cipher(self, cipher, 13)
      check_cipher(self, cipher, 79)