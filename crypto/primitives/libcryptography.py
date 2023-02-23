from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers import algorithms, modes
from cryptography.hazmat.primitives.kdf import scrypt

from utils.abstract import *

from ..base.base import CipherMeta, BaseCipher, FixHash, VarHash, BlockCipher
from ..base.parameters import Parameter


# pylint: disable=invalid-name
# pylint: disable=no-self-argument,no-value-for-parameter


__all__ = [
    "VarHashShake128",
    "VarHashShake256",

    "VarHashScrypt",

    "Hash224SHA3",
    "Hash256SHA3",
    "Hash384SHA3",
    "Hash512SHA3",

    "Hash512BLAKE2",

    "Hash128Scrypt",
    "Hash256Scrypt",
    "Hash512Scrypt",

    "Enc256AESCTR",
    "Dec256AESCTR",

    "Enc256CHACHA",
    "Dec256CHACHA",

    "Enc256CAMELLIACTR",
    "Dec256CAMELLIACTR",
]


# ***************
# ***************
# ***************
# *************** VAR HASHES
# *************** ID = 100 - 299


class ShakeBase(VarHash):

    @abstractclsattrib
    def IMPLEMENTATION(cls, i):
        pass

    def _process(self, data):
        instance = hashes.Hash(self.IMPLEMENTATION(self.digest_size))
        instance.update(data)
        return instance.finalize()


class VarHashShake128(ShakeBase):

    ALGORITHM_ID = 100
    IMPLEMENTATION = hashes.SHAKE128


class VarHashShake256(ShakeBase):

    ALGORITHM_ID = 101
    IMPLEMENTATION = hashes.SHAKE256


class VarHashScrypt(VarHash):

    ALGORITHM_ID = 110

    @Parameter(bytes)
    def salt(self, value):
        assert len(value) >= 16

    @Parameter(int)
    def n(self, value):
        assert value >= 2 ** 14

    @Parameter(int)
    def r(self, value):
        pass

    def _process(self, data):
        impl = scrypt.Scrypt(self.salt, self.digest_size, self.n, self.r, 1)
        return impl.derive(data)


# ***************
# ***************
# ***************
# *************** FIX HASHES
# *************** ID = 300 - 999


class ShaBase(FixHash):

    @abstractclsattrib
    def IMPLEMENTATION(cls, i):
        pass

    def _process(self, data):
        instance = hashes.Hash(self.IMPLEMENTATION())
        instance.update(data)
        return instance.finalize()


class Hash224SHA3(ShaBase):

    ALGORITHM_ID = 310
    DIGEST_SIZE = 28
    IMPLEMENTATION = hashes.SHA3_224


class Hash256SHA3(ShaBase):

    ALGORITHM_ID = 311
    DIGEST_SIZE = 32
    IMPLEMENTATION = hashes.SHA3_256


class Hash384SHA3(ShaBase):

    ALGORITHM_ID = 312
    DIGEST_SIZE = 48
    IMPLEMENTATION = hashes.SHA3_384


class Hash512SHA3(ShaBase):

    ALGORITHM_ID = 313
    DIGEST_SIZE = 64
    IMPLEMENTATION = hashes.SHA3_512


class Hash512BLAKE2(FixHash):

    ALGORITHM_ID = 320
    DIGEST_SIZE = 64

    def _process(self, data):
        instance = hashes.Hash(hashes.BLAKE2b(64))
        instance.update(data)
        return instance.finalize()


class FixScryptBase(FixHash):

    @Parameter(bytes)
    def salt(self, value):
        assert len(value) >= 16

    @Parameter(int)
    def n(self, value):
        assert value >= 2 ** 14

    @Parameter(int)
    def r(self, value):
        pass

    def _process(self, data):
        instance = scrypt.Scrypt(self.salt, self.DIGEST_SIZE, self.n, self.r, 1)
        return instance.derive(data)


class Hash128Scrypt(FixScryptBase):

    ALGORITHM_ID = 400
    DIGEST_SIZE = 16


class Hash256Scrypt(FixScryptBase):

    ALGORITHM_ID = 401
    DIGEST_SIZE = 32


class Hash512Scrypt(FixScryptBase):

    ALGORITHM_ID = 402
    DIGEST_SIZE = 64


# ***************
# ***************
# ***************
# *************** CIPHERS
# *************** ID = 1000 - 1999


def create_cipher(cipher_cls, algorithm_id):
    cipher_name = cipher_cls.__name__.replace('Cipher', '', 1)
    encryptor = CipherMeta(f"Enc{cipher_name}", (cipher_cls,), {"ALGORITHM_ID": algorithm_id})
    decryptor = CipherMeta(f"Dec{cipher_name}", (cipher_cls,), {"ALGORITHM_ID": algorithm_id})
    return encryptor, decryptor


class Cipher256AESCTR(BlockCipher):

    KEY_SIZE = 32
    BLOCK_SIZE = 16
    IV_SIZE = BLOCK_SIZE

    def _process(self, data):
        instance = ciphers.Cipher(algorithms.AES(self.key), modes.CTR(self.iv))
        if self.IS_ENCRYPTOR:
            instance = instance.encryptor()
        else:
            instance = instance.decryptor()
        # pylint: disable-next=no-member,useless-suppression
        return instance.update(data) + instance.finalize()


Enc256AESCTR, Dec256AESCTR = create_cipher(Cipher256AESCTR, 1000)


class Cipher256CHACHA(BaseCipher):

    KEY_SIZE = 32
    IV_SIZE = 16

    def _process(self, data):
        instance = ciphers.Cipher(algorithms.ChaCha20(self.key, self.iv), None)
        if self.IS_ENCRYPTOR:
            instance = instance.encryptor()
        else:
            instance = instance.decryptor()
        # pylint: disable-next=no-member,useless-suppression
        return instance.update(data) + instance.finalize()


Enc256CHACHA, Dec256CHACHA = create_cipher(Cipher256CHACHA, 1010)


class Cipher256CAMELLIACTR(BlockCipher):

    KEY_SIZE = 32
    BLOCK_SIZE = 16
    IV_SIZE = BLOCK_SIZE

    def _process(self, data):
        instance = ciphers.Cipher(algorithms.Camellia(self.key), modes.CTR(self.iv))
        if self.IS_ENCRYPTOR:
            instance = instance.encryptor()
        else:
            instance = instance.decryptor()
        # pylint: disable-next=no-member,useless-suppression
        return instance.update(data) + instance.finalize()


Enc256CAMELLIACTR, Dec256CAMELLIACTR = create_cipher(Cipher256CAMELLIACTR, 1020)
