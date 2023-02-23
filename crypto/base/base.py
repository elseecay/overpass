import re
import secrets

from utils.abstract import *
from utils.common import typename

from .parameters import *


# pylint: disable=no-self-argument, no-value-for-parameter
# pylint: disable=invalid-name


# **************
# **************
# **************
# ************** ALGORITHM


ALGORITHMS, ALGORITHMS_BY_NAME = {}, {}


class CryptoAlgorithmMeta(ParametersContainerMeta, ABCMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        if isabstract(cls):
            return
        is_hash, is_cipher = int(issubclass(cls, BaseHash)), int(issubclass(cls, BaseCipher))
        assert is_hash + is_cipher == 1, f"Class {cls.__name__} should be child of BaseHash or BaseCipher"
        cls._meta_register()

    @abstractmethod
    def _meta_register(cls):
        pass


class BaseCryptoAlgorithm(ParametersContainer, ABC, metaclass=CryptoAlgorithmMeta):

    @parameters_init_simplifier
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractclsattrib
    def ALGORITHM_ID(cls, value):
        assert isinstance(value, int) and value > 0, "Algorithm ID should be positive int"

    @abstractmethod
    def _process(self, data):
        pass

    def process(self, data: bytes):
        data = self._process(data)
        return data


# ***************
# ***************
# ***************
# *************** HASH


class HashMeta(CryptoAlgorithmMeta):

    FIX_HASH_NAMING = re.compile(r"Hash(\d+)\w+")
    VAR_HASH_NAMING = re.compile(r"VarHash\w+")

    def _meta_register(cls):
        is_fix, is_var = issubclass(cls, FixHash), issubclass(cls, VarHash)
        assert is_fix + is_var == 1, "Class should be child of FixHash or VarHash"
        NAMING = HashMeta.FIX_HASH_NAMING if is_fix else HashMeta.VAR_HASH_NAMING
        match = NAMING.fullmatch(cls.__name__)
        assert match, f"Bad class name for {typename(cls)}"
        if is_fix:
            naming_dlen = int(match.group(1))
            cls_dlen = cls.DIGEST_SIZE << 3
            assert cls_dlen == naming_dlen, f"Digest length {naming_dlen} does not match to actual {cls_dlen} for class {typename(cls)}"
        cls._meta_add_algorithm()

    def _meta_add_algorithm(cls):
        if cls.ALGORITHM_ID in ALGORITHMS:
            assert False, f"Cannot set algorithm id {cls.ALGORITHM_ID} for class {typename(cls)}, already defined in {typename(ALGORITHMS[cls.ALGORITHM_ID])}"
        ALGORITHMS[cls.ALGORITHM_ID] = cls
        ALGORITHMS_BY_NAME[cls.__name__] = cls


class BaseHash(BaseCryptoAlgorithm, metaclass=HashMeta):

    @abstractmethod
    def get_digest_size(self):
        pass


class FixHash(BaseHash):

    @abstractclsattrib
    def DIGEST_SIZE(cls, value):
        assert isinstance(value, int) and value > 0, "Digest size should be a positive int"

    def get_digest_size(self):
        return self.DIGEST_SIZE


class VarHash(BaseHash):

    @Parameter(int)
    def digest_size(self, value):
        assert value > 0, "Digest size should be a positive int"

    def get_digest_size(self):
        return self.digest_size


# ***************
# ***************
# ***************
# *************** CIPHER


class CipherMeta(CryptoAlgorithmMeta):

    NAMING = re.compile(r"(Enc|Dec)(\d+)\w+")

    def _meta_register(cls):
        match = CipherMeta.NAMING.fullmatch(cls.__name__)
        assert match, f"Bad class name for {typename(cls)}"
        assert issubclass(cls, BaseCipher)
        naming_ksize = int(match.group(2))
        cls_ksize = cls.KEY_SIZE << 3
        assert cls_ksize == naming_ksize, f"Key size {naming_ksize} does not match to actual {cls_ksize} for class {typename(cls)}"
        cls._meta_add_algorithm()

    def _meta_add_algorithm(cls):
        if ALGORITHMS.get(cls.ALGORITHM_ID, None) is None:
            ALGORITHMS[cls.ALGORITHM_ID] = {}
        container = ALGORITHMS[cls.ALGORITHM_ID]
        assert len(container) < 2
        if cls.__name__.startswith("Enc"):
            assert "enc" not in container, f"Redefinition of enryptor for id = {cls.ALGORITHM_ID}"
            container["enc"] = cls
        else:
            assert "dec" not in container, f"Redefinition of decryptor for id = {cls.ALGORITHM_ID}"
            container["dec"] = cls
        if len(container) == 2:
            enc, dec = container["enc"], container["dec"]
            enc.IS_ENCRYPTOR, dec.IS_ENCRYPTOR = True, False
            enc.IS_DECRYPTOR, dec.IS_DECRYPTOR = False, True
            enc.ENCRYPTOR_CLS, dec.ENCRYPTOR_CLS = enc, enc
            enc.DECRYPTOR_CLS, dec.DECRYPTOR_CLS = dec, dec
            assert enc.ALGORITHM_ID == dec.ALGORITHM_ID, f"'{typename(enc)}' and '{typename(dec)}' have different algorithm ID"
        ALGORITHMS_BY_NAME[cls.__name__] = cls


class BaseCipher(BaseCryptoAlgorithm, metaclass=CipherMeta):

    IS_ENCRYPTOR: bool
    IS_DECRYPTOR: bool
    ENCRYPTOR_CLS: "BaseCipher"
    DECRYPTOR_CLS: "BaseCipher"

    @abstractclsattrib
    def KEY_SIZE(cls, value):
        assert isinstance(value, int), "Key length should be an int"
        assert value >= 16, "Key size should be >= 16 bytes"

    @abstractclsattrib
    def IV_SIZE(cls, value):
        assert isinstance(value, int), "IV_SIZE should be an int"
        assert value >= 16, "IV_SIZE should be >= 16 bytes"

    @Parameter(bytes, required=False)
    def key(self, value):
        # pylint: disable=comparison-with-callable
        assert len(value) == self.KEY_SIZE

    @Parameter(bytes, required=False)
    def iv(self, value):
        # pylint: disable=comparison-with-callable
        assert len(value) == self.IV_SIZE

    def process(self, data: bytes):
        assert hasattr(self, "key") and hasattr(self, "iv")
        return super().process(data)

    def iv_set_random(self) -> bytes:
        self.iv = secrets.token_bytes(self.IV_SIZE)
        return self.iv

    def opposite_instance(self):
        opp_cls = self.DECRYPTOR_CLS if self.IS_ENCRYPTOR else self.ENCRYPTOR_CLS
        return opp_cls(parameters=self.get_instance_parameters())


class BlockCipher(BaseCipher):

    @abstractclsattrib
    def BLOCK_SIZE(cls, value):
        assert isinstance(value, int) and value > 0, "Block size should be a positive int"
