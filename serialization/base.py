from utils.abstract import *


# pylint: disable=redefined-builtin
# pylint: disable=no-self-argument
# pylint: disable=invalid-name


# Positive IDs for user


ID_KEY = "$$"


CLASS_BY_ID, ID_BY_CLASS, SERIALIZER_BY_ID, SERIALIZER_BY_CLASS = {}, {}, {}, {}


def assign_serialization_id(serializer, cls, id):
    assert cls not in ID_BY_CLASS and id not in CLASS_BY_ID
    assert isinstance(cls, type)
    ID_BY_CLASS[cls] = id
    CLASS_BY_ID[id] = cls
    SERIALIZER_BY_ID[id] = serializer
    SERIALIZER_BY_CLASS[cls] = serializer


# JSON builtins
BUILTIN_ID = {
    None.__class__: -1,
    bool: -2,
    int: -3,
    float: -4,
    str: -5,
    list: -6
}


def get_data_id(data) -> int:
    if isinstance(data, dict):
        return data.get(ID_KEY)
    data_type = type(data)
    return BUILTIN_ID[data_type]


def find_serializer_by_class(cls):
    return SERIALIZER_BY_CLASS[cls]


def find_serializer_by_data(data):
    id = get_data_id(data)
    return SERIALIZER_BY_ID[id]


def serialize(value):
    cls = type(value)
    serializer = find_serializer_by_class(cls)
    return serializer.serialize(value)


def deserialize(data):
    serializer = find_serializer_by_data(data)
    return serializer.deserialize(data)


class SerializerMeta(ABCMeta):

    def __init__(cls, name, bases, attribs):
        super().__init__(name, bases, attribs)
        if isabstract(cls):
            return
        assign_serialization_id(cls, cls.CLASS, cls.ID)


class SerializerBase(ABC, metaclass=SerializerMeta):

    @abstractclsattrib
    def ID(cls, val):
        pass

    @abstractclsattrib
    def CLASS(cls, val):
        pass

    @classmethod
    @abstractmethod
    def serialize(cls, obj: object) -> dict:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: dict) -> object:
        pass


class SerializerAttrib(SerializerBase):

    @classmethod
    def serialize(cls, obj):
        result = {k: serialize(v) for k, v in vars(obj).items() if cls.is_attribute_serializable(k, v)}
        result[ID_KEY] = cls.ID
        return result

    @classmethod
    def deserialize(cls, data):
        # pylint: disable-next=no-value-for-parameter
        result = cls.CLASS.__new__(cls.CLASS)
        data.pop(ID_KEY)
        for k, v in data.items():
            setattr(result, k, deserialize(v))
        return result

    @staticmethod
    @abstractmethod
    def is_attribute_serializable(name, value=None):
        pass


class SerializerAttribTrivial(SerializerAttrib):

    def is_attribute_serializable(name, value=None):
        return True
