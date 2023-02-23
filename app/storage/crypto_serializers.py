from crypto import primitives

from crypto.base.base import BaseCipher, BaseHash, CryptoAlgorithmMeta
from crypto.base.parameters import ParametersContainer
from crypto.mixer import Mixer, Hasher, KeyHasher

from serialization.base import SerializerBase, SerializerMeta
from serialization.driver import ObjectDriver


def _register_algorithm_serializer(cls):
    SerializerMeta(f"Serializer{cls.__name__}", (ParametersContainerSerializer,), {"CLASS": cls, "ID": cls.ALGORITHM_ID})


def _register_all_algorithms_serializers():
    for name in dir(primitives):
        cls = getattr(primitives, name)
        if not isinstance(cls, CryptoAlgorithmMeta):
            continue
        if issubclass(cls, BaseHash) or (issubclass(cls, BaseCipher) and cls.IS_ENCRYPTOR):
            _register_algorithm_serializer(cls)


class ParametersContainerSerializer(SerializerBase):

    @classmethod
    def serialize(cls, obj: ParametersContainer) -> dict:
        driver = ObjectDriver.create_empty(cls.ID)
        params = obj.get_instance_parameters()
        if "key" in params:
            del params["key"]
        for k, v in params.items():
            driver.add_key(k, v)
        return driver.data

    @classmethod
    def deserialize(cls, data: dict) -> ParametersContainer:
        driver = ObjectDriver.attach(data)
        params = {k: driver.get_key(k) for k in driver.iter_keys()}
        # pylint: disable-next=unexpected-keyword-arg, no-value-for-parameter
        return cls.CLASS(parameters=params)


class MixerSerializer(SerializerBase):

    ID = 2000
    CLASS = Mixer

    @classmethod
    def serialize(cls, obj: Mixer) -> dict:
        driver = ObjectDriver.create_empty(MixerSerializer.ID)
        driver.add_key("elements", obj.elements)
        return driver.data

    @classmethod
    def deserialize(cls, data: dict) -> Mixer:
        driver = ObjectDriver.attach(data)
        elements = driver.get_key("elements")
        return Mixer(*elements)


class HasherSerializer(SerializerBase):

    ID = 2001
    CLASS = Hasher

    @classmethod
    def serialize(cls, obj: Hasher) -> dict:
        driver = ObjectDriver.create_empty(HasherSerializer.ID)
        driver.add_key("elements", obj.elements)
        driver.add_key("iterations", obj.iterations)
        return driver.data

    @classmethod
    def deserialize(cls, data: dict) -> Hasher:
        driver = ObjectDriver.attach(data)
        elements = driver.get_key("elements")
        iterations = driver.get_key("iterations")
        return Hasher(*elements, iterations=iterations)


class KeyHasherSerializer(SerializerBase):

    ID = 2002
    CLASS = KeyHasher

    @classmethod
    def serialize(cls, obj: KeyHasher) -> dict:
        driver = ObjectDriver.create_empty(KeyHasherSerializer.ID)
        driver.add_key("elements", obj.elements)
        return driver.data

    @classmethod
    def deserialize(cls, data: dict) -> KeyHasher:
        driver = ObjectDriver.attach(data)
        elements = driver.get_key("elements")
        return KeyHasher(*elements)


_register_all_algorithms_serializers()
