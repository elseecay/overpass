import base64

from .base import serialize, deserialize, BUILTIN_ID, SerializerBase, SerializerMeta, ID_KEY


# pylint: disable=redefined-builtin


def _create_trivial_builtin_serializer(cls, id):
    attribs = {
        "serialize": classmethod(lambda cls, obj: obj),
        "deserialize": classmethod(lambda cls, data: data),
        "CLASS": cls,
        "ID": id
    }
    return SerializerMeta(f"BuiltinSerializer{cls.__name__.title()}", (SerializerBase,), attribs)


_create_trivial_builtin_serializer(None.__class__, BUILTIN_ID[None.__class__])
_create_trivial_builtin_serializer(bool, BUILTIN_ID[bool])
_create_trivial_builtin_serializer(int, BUILTIN_ID[int])
_create_trivial_builtin_serializer(float, BUILTIN_ID[float])
_create_trivial_builtin_serializer(str, BUILTIN_ID[str])


class BuiltinSerializerList(SerializerBase):

    ID = BUILTIN_ID[list]
    CLASS = list

    @classmethod
    def serialize(cls, obj: list) -> list:
        return [serialize(item) for item in obj]

    @classmethod
    def deserialize(cls, data) -> list:
        return [deserialize(item) for item in data]


class BuiltinSerializerTuple(SerializerBase):

    ID = -7
    CLASS = tuple

    @classmethod
    def serialize(cls, obj: tuple) -> dict:
        return {
            ID_KEY: BuiltinSerializerTuple.ID,
            "v": serialize(list(obj))
        }

    @classmethod
    def deserialize(cls, data) -> tuple:
        return tuple(deserialize(data["v"]))


class BuiltinSerializerSet(SerializerBase):

    ID = -8
    CLASS = set

    @classmethod
    def serialize(cls, obj: set) -> dict:
        return {
            ID_KEY: BuiltinSerializerSet.ID,
            "k": serialize(list(obj))
        }

    @classmethod
    def deserialize(cls, data) -> set:
        return set(deserialize(data["k"]))


class BuiltinSerializerFrozenSet(SerializerBase):

    ID = -9
    CLASS = frozenset

    @classmethod
    def serialize(cls, obj: frozenset) -> dict:
        return {
            ID_KEY: BuiltinSerializerFrozenSet.ID,
            "k": serialize(list(obj))
        }

    @classmethod
    def deserialize(cls, data) -> frozenset:
        return frozenset(deserialize(data["k"]))


class BuiltinSerializerDict(SerializerBase):

    ID = -10
    CLASS = dict

    @classmethod
    def serialize(cls, obj: dict) -> dict:
        return {
            ID_KEY: BuiltinSerializerDict.ID,
            "i": serialize(list(obj.items()))
        }

    @classmethod
    def deserialize(cls, data) -> dict:
        return dict(deserialize(data["i"]))


class BuiltinSerializerBytes(SerializerBase):

    ID = -11
    CLASS = bytes

    @classmethod
    def serialize(cls, obj) -> dict:
        return {
            ID_KEY: BuiltinSerializerBytes.ID,
            "v": base64.standard_b64encode(obj).decode("ascii")
        }

    @classmethod
    def deserialize(cls, data) -> bytes:
        return base64.standard_b64decode(data["v"])


class BuiltinSerializerBytearray(SerializerBase):

    ID = -12
    CLASS = bytearray

    @classmethod
    def serialize(cls, obj) -> dict:
        return {
            ID_KEY: BuiltinSerializerBytearray.ID,
            "v": base64.standard_b64encode(obj).decode("ascii")
        }

    @classmethod
    def deserialize(cls, data) -> bytearray:
        return bytearray(base64.standard_b64decode(data["v"]))


class BuiltinSerializerRange(SerializerBase):

    ID = -13
    CLASS = range

    @classmethod
    def serialize(cls, obj: range) -> dict:
        return {
            ID_KEY: BuiltinSerializerRange.ID,
            "b": obj.start,
            "e": obj.stop,
            "s": obj.step
        }

    @classmethod
    def deserialize(cls, data) -> range:
        return range(data["b"], data["e"], data["s"])


class BuiltinSerializerEllipsis(SerializerBase):

    ID = -14
    CLASS = Ellipsis.__class__

    @classmethod
    def serialize(cls, obj: Ellipsis.__class__) -> dict:
        return {ID_KEY: BuiltinSerializerEllipsis.ID}

    @classmethod
    def deserialize(cls, data) -> Ellipsis.__class__:
        return ...
