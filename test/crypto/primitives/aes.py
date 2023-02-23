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


class AesCtrRfcTests(TestCase):

   def test_0(self):
      ctr = bytes.fromhex('001CC5B751A51D70A1C1114800000001')
      key = bytes.fromhex('FF7A617CE69148E4F1726E2F43581DE2AA62D9F805532EDFF1EED687FB54153D')
      plain_text = bytes.fromhex('000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F20212223')
      cipher_text = bytes.fromhex('EB6C52821D0BBBF7CE7594462ACA4FAAB407DF866569FD07F48CC0B583D6071F1EC0E6B8')
      encryptor = p.Enc256AESCTR(iv=ctr, key=key)
      decryptor = encryptor.opposite_instance()
      self.assertEqual(encryptor.process(plain_text), cipher_text)
      self.assertEqual(decryptor.process(cipher_text), plain_text)

   def test_1(self):
      ctr = bytes.fromhex('00 FA AC 24 C1 58 5E F1 5A 43 D8 75 00 00 00 01')
      key = bytes.fromhex('F6 D6 6D 6B D5 2D 59 BB 07 96 36 58 79 EF F8 86 C6 6D D5 1A 5B 6A 99 74 4B 50 59 0C 87 A2 38 84')
      plain_text = bytes.fromhex('00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F')
      cipher_text = bytes.fromhex('F0 5E 23 1B 38 94 61 2C 49 EE 00 0B 80 4E B2 A9 B8 30 6B 50 8F 83 9D 6A 55 30 83 1D 93 44 AF 1C')
      encryptor = p.Enc256AESCTR(iv=ctr, key=key)
      decryptor = encryptor.opposite_instance()
      self.assertEqual(encryptor.process(plain_text), cipher_text)
      self.assertEqual(decryptor.process(cipher_text), plain_text)

   def test_2(self):
      ctr = bytes.fromhex('00 00 00 60 DB 56 72 C9 7A A8 F0 B2 00 00 00 01')
      key = bytes.fromhex('77 6B EF F2 85 1D B0 6F 4C 8A 05 42 C8 69 6F 6C 6A 81 AF 1E EC 96 B4 D3 7F C1 D6 89 E6 C1 C1 04')
      plain_text = 'Single block msg'.encode("utf-8")
      cipher_text = bytes.fromhex('14 5A D0 1D BF 82 4E C7 56 08 63 DC 71 E3 E0 C0')
      encryptor = p.Enc256AESCTR(iv=ctr, key=key)
      decryptor = encryptor.opposite_instance()
      self.assertEqual(encryptor.process(plain_text), cipher_text)
      self.assertEqual(decryptor.process(cipher_text), plain_text)


class AesCtrTests(TestCase):

   def test_1(self):
      cipher = p.Enc256AESCTR(iv=b"1" * 16, key=b"1" * 32)
      check_cipher(self, cipher, 1024)

   def test_2(self):
      cipher = p.Enc256AESCTR(iv=b"2" * 16, key=b"2" * 32)
      check_cipher(self, cipher, 1024 * 128)
      check_cipher(self, cipher, 1024 * 256)
      check_cipher(self, cipher, 1024 * 512)
      check_cipher(self, cipher, 1024 * 1024)

   def test_3(self):
      cipher = p.Enc256AESCTR(iv=b"3" * 16, key=b"3" * 32)
      check_cipher(self, cipher, 1)
      check_cipher(self, cipher, 2)
      check_cipher(self, cipher, 13)
      check_cipher(self, cipher, 79)

